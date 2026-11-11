"""Agent runs as a service: start in the background, follow events, cancel (AGT-02, AGT-03).

`start` accepts a turn, returns the `AgentRun` immediately and executes the agent loop on a
worker thread. Listeners attach to the live `RunEventBroker`; finished runs older than the
broker's window are replayed from the persisted run and its steps.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator

from personal_agent.application.run_events import RunEventBroker
from personal_agent.application.security.approvals import approval_event_data
from personal_agent.application.services.chat_service import ChatService, PreparedTurn
from personal_agent.domain.approvals import Approval, ApprovalStatus
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import (
    AgentRun,
    CancellationToken,
    RunEvent,
    RunStatus,
    RunStep,
    StepStatus,
)
from personal_agent.domain.ports import AgentRunRepository, ApprovalStore

logger = logging.getLogger(__name__)


class RunService:
    def __init__(
        self,
        *,
        chat: ChatService,
        runs: AgentRunRepository,
        broker: RunEventBroker,
        approvals: ApprovalStore | None = None,
    ) -> None:
        self._chat = chat
        self._runs = runs
        self._broker = broker
        self._approvals = approvals
        self._tokens: dict[str, CancellationToken] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    # -- lifecycle -----------------------------------------------------------

    def start(
        self,
        *,
        user_id: str,
        text: str,
        session_id: str | None = None,
        origin: str = "dashboard",
        wait: bool = False,
    ) -> AgentRun:
        """Open a run and execute it in the background (or inline with `wait=True`)."""
        if not text.strip():
            raise ValueError("Message is required.")
        prepared = self._chat.begin_turn(
            user_id=user_id, session_id=session_id, text=text, origin=origin
        )
        assert isinstance(prepared, PreparedTurn)  # blank input was rejected above
        token = CancellationToken()
        with self._lock:
            self._tokens[prepared.run.id] = token
        thread = threading.Thread(
            target=self._execute,
            args=(prepared, token),
            daemon=True,
            name=f"run-{prepared.run.id[:8]}",
        )
        with self._lock:
            self._threads[prepared.run.id] = thread
        thread.start()
        if wait:
            thread.join()
        return prepared.run

    def _execute(self, prepared: PreparedTurn, token: CancellationToken) -> None:
        run_id = prepared.run.id
        try:
            self._chat.run_prepared(prepared, cancel=token)
        except Exception:  # noqa: BLE001 — already recorded on the run as failed
            logger.warning("Run %s failed", run_id, exc_info=True)
        finally:
            with self._lock:
                self._tokens.pop(run_id, None)
                self._threads.pop(run_id, None)

    # -- pause / resume (APR-02) ---------------------------------------------

    def resume_after_execution(
        self, approval: Approval, *, output: str, ok: bool, wait: bool = False
    ) -> None:
        """Continue the paused run on a worker thread after its approved tool ran."""
        run = self._chat.awaiting_run(approval.run_id or "")
        if run is None:
            return
        self._reopen(run)
        token = CancellationToken()  # also enables token streaming for the resumed turn
        with self._lock:
            self._tokens[run.id] = token
        thread = threading.Thread(
            target=self._resume,
            args=(approval, output, ok, token),
            daemon=True,
            name=f"resume-{run.id[:8]}",
        )
        with self._lock:
            self._threads[run.id] = thread
        thread.start()
        if wait:
            thread.join()

    def _resume(self, approval: Approval, output: str, ok: bool, token: CancellationToken) -> None:
        run_id = approval.run_id or ""
        try:
            self._chat.resume_run(
                run_id,
                approval_id=approval.id,
                call_id=approval.call_id,
                tool_name=approval.tool_name,
                output=output,
                ok=ok,
                untrusted=approval.untrusted_content,
                cancel=token,
            )
        except Exception:  # noqa: BLE001 — already recorded on the run as failed
            logger.warning("Resuming run %s failed", run_id, exc_info=True)
        finally:
            with self._lock:
                self._tokens.pop(run_id, None)
                self._threads.pop(run_id, None)

    def conclude_declined(self, approval: Approval, *, message: str) -> None:
        """Finish a paused run whose approval was denied or expired."""
        run = self._chat.awaiting_run(approval.run_id or "")
        if run is None:
            return
        self._reopen(run)
        self._chat.conclude_declined(
            run.id,
            approval_id=approval.id,
            call_id=approval.call_id,
            tool_name=approval.tool_name,
            decision=approval.status.value,
            message=message,
        )

    def _reopen(self, run: AgentRun) -> None:
        """Make the run's stream live again; rebuild it from storage after a restart."""
        seed = [] if self._broker.has(run.id) else self._replay(run)
        self._broker.reopen(run.id, seed)

    def cancel(self, run_id: str) -> AgentRun:
        """Ask a running run to stop before its next step; idempotent for finished runs."""
        run = self.get(run_id)
        with self._lock:
            token = self._tokens.get(run_id)
        if token is not None and not run.status.is_terminal:
            token.cancel()
        return run

    def join(self, run_id: str, timeout: float = 10.0) -> None:
        """Wait for a run's worker to finish (tests, shutdown)."""
        with self._lock:
            thread = self._threads.get(run_id)
        if thread is not None:
            thread.join(timeout)

    # -- reads ---------------------------------------------------------------

    def get(self, run_id: str) -> AgentRun:
        run = self._runs.get(run_id)
        if run is None:
            raise StorageError("Unknown run.")
        return run

    def list_recent(self, user_id: str | None = None, limit: int = 50) -> list[AgentRun]:
        return self._runs.list_recent(user_id=user_id, limit=limit)

    def steps(self, run_id: str) -> list[RunStep]:
        return self._runs.list_steps(run_id)

    def events(
        self, run_id: str, after_seq: int = 0, idle_timeout: float = 5.0
    ) -> Iterator[RunEvent | None]:
        """Live events when the run is in memory (None = keep-alive), otherwise a replay."""
        run = self.get(run_id)
        if self._broker.has(run_id):
            yield from self._broker.follow(run_id, after_seq, idle_timeout)
            return
        yield from (e for e in self._replay(run) if e.seq > after_seq)

    def _replay(self, run: AgentRun) -> list[RunEvent]:
        """Reconstruct the structural events of a finished run from storage (no tokens)."""
        data: list[tuple[str, dict[str, object]]] = [
            (
                "run.started",
                {
                    "session_id": run.session_id,
                    "origin": run.origin,
                    "prompt_version": run.prompt_version,
                },
            )
        ]
        for step in self._runs.list_steps(run.id):
            base = {"call_id": step.id, "name": step.name}
            data.append(("tool.started", {**base, "arguments": step.arguments}))
            if step.status is not StepStatus.RUNNING:
                data.append(
                    (
                        "tool.finished",
                        {
                            **base,
                            "ok": step.status is StepStatus.OK,
                            "output": step.output or step.error,
                            "duration_ms": step.duration_ms,
                        },
                    )
                )
        if run.status is RunStatus.COMPLETED:
            data.append(
                (
                    "run.completed",
                    {
                        "session_id": run.session_id,
                        "reply": run.final_text,
                        "stop_reason": run.stop_reason,
                    },
                )
            )
        elif run.status is RunStatus.CANCELLED:
            data.append(
                (
                    "run.failed",
                    {"status": "cancelled", "reply": run.final_text, "stop_reason": "cancelled"},
                )
            )
        elif run.status is RunStatus.FAILED:
            data.append(("run.failed", {"status": "failed", "error": run.error}))
        elif run.status is RunStatus.AWAITING_APPROVAL and self._approvals is not None:
            latest = [
                a
                for a in self._approvals.find(run_id=run.id, limit=20)
                if a.status is not ApprovalStatus.SUPERSEDED
            ]
            if latest:
                data.append(("approval.required", approval_event_data(latest[0], durable=True)))
        return [
            RunEvent(run_id=run.id, type=kind, data=payload, seq=index + 1)
            for index, (kind, payload) in enumerate(data)
        ]
