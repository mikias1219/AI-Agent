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
from personal_agent.application.services.chat_service import ChatService, PreparedTurn
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import (
    AgentRun,
    CancellationToken,
    RunEvent,
    RunStatus,
    RunStep,
    StepStatus,
)
from personal_agent.domain.ports import AgentRunRepository

logger = logging.getLogger(__name__)


class RunService:
    def __init__(
        self,
        *,
        chat: ChatService,
        runs: AgentRunRepository,
        broker: RunEventBroker,
    ) -> None:
        self._chat = chat
        self._runs = runs
        self._broker = broker
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
        return [
            RunEvent(run_id=run.id, type=kind, data=payload, seq=index + 1)
            for index, (kind, payload) in enumerate(data)
        ]
