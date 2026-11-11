"""Chat use case shared by CLI, Telegram, and the authenticated web API.

One turn = load session → build the versioned system prompt → open an `AgentRun` → run the
agent (which may call tools through the enforcement gate) → persist every message → finish
the run → return the final text. Every turn is therefore a persisted run with events
(AGT-01, AGT-02), whichever interface started it.

The turn is split in two so the runs API can return a run id immediately:
`begin_turn` (synchronous, cheap) and `run_prepared` (the slow agent loop).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from personal_agent.application.agent import Agent
from personal_agent.application.run_events import emit_event
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.domain.conversation import (
    arrange_tool_results,
    omit_retired_tool_messages,
)
from personal_agent.domain.dates import get_zone
from personal_agent.domain.exceptions import AgentError, StorageError
from personal_agent.domain.models import (
    AgentRun,
    CancellationToken,
    Message,
    OwnerProfile,
    RunOutcome,
    RunStatus,
    ToolContext,
)
from personal_agent.domain.ports import (
    AgentRunRepository,
    AuditLog,
    ConversationRepository,
    EventSink,
    MemoryStore,
)
from personal_agent.prompts import render_system_prompt

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "The agent could not complete this reply."


@dataclass(slots=True)
class PreparedTurn:
    """A turn that has been accepted and recorded but not yet executed."""

    run: AgentRun
    history: list[Message]
    ctx: ToolContext
    user_id: str  # audit actor
    session_id: str


class ChatService:
    """Turn-oriented chat orchestration, interface-agnostic."""

    def __init__(
        self,
        *,
        agent: Agent,
        conversations: ConversationRepository,
        memory: MemoryStore,
        audit: AuditLog | None = None,
        history_limit: int = 20,
        runs: AgentRunRepository | None = None,
        events: EventSink | None = None,
        profiles: ProfileService | None = None,
        model_label: str = "",
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._agent = agent
        self._conversations = conversations
        self._memory = memory
        self._audit = audit
        self._history_limit = history_limit
        self._runs = runs
        self._events = events
        self._profiles = profiles
        self._model_label = model_label
        self._clock = clock

    def latest_session(self, user_id: str) -> str | None:
        return self._conversations.latest_session(user_id)

    def start_session(self, user_id: str, origin: str) -> str:
        session_id = self._conversations.create_session(user_id)
        self._record(
            "conversation.session_created", user_id, {"session_id": session_id, "origin": origin}
        )
        return session_id

    def turn(
        self,
        *,
        user_id: str = "default",
        session_id: str | None = None,
        text: str,
        origin: str = "cli",
        identity_user_id: str | None = None,
        on_token: Callable[[str], None] | None = None,
        cancel: CancellationToken | None = None,
    ) -> tuple[str, str]:
        """Run one chat turn; returns (session_id, assistant_text).

        A new session id is created when `session_id` is None, so callers can
        resume conversations across CLI/API/Telegram without knowing storage.
        """
        prepared = self.begin_turn(
            user_id=user_id,
            session_id=session_id,
            text=text,
            origin=origin,
            identity_user_id=identity_user_id,
        )
        if isinstance(prepared, str):  # empty input: only a session id comes back
            return prepared, ""
        return self.run_prepared(prepared, on_token=on_token, cancel=cancel)

    def begin_turn(
        self,
        *,
        user_id: str = "default",
        session_id: str | None = None,
        text: str,
        origin: str = "cli",
        identity_user_id: str | None = None,
    ) -> PreparedTurn | str:
        """Accept a turn: store the user message and open the run (status `running`).

        Returns the session id alone for blank input, which starts no run.
        """
        text = text.strip()
        if not text:
            return session_id or self._conversations.create_session(user_id)

        if session_id is None:
            session_id = self._conversations.create_session(user_id)
            self._record(
                "conversation.session_created",
                user_id,
                {"session_id": session_id, "origin": origin},
            )
        identity = identity_user_id or user_id

        self._conversations.append(session_id, Message(role="user", content=text))
        self._record(
            "chat.user_message",
            user_id,
            {"session_id": session_id, "origin": origin, "character_count": len(text)},
        )
        history = self._conversations.load(session_id, limit=self._history_limit)
        history = arrange_tool_results(omit_retired_tool_messages(history, {"noop"}))
        system = self._system_message(identity)
        history = [system[0], *history]

        run = AgentRun(
            id=uuid.uuid4().hex,
            session_id=session_id,
            user_id=identity,
            origin=origin,
            prompt_version=system[1],
            status=RunStatus.RUNNING,
            input_text=text,
            model=self._model_label,
            created_at=self._clock(),
        )
        if self._runs is not None:
            self._runs.create(run)
        ctx = ToolContext(
            user_id=identity,
            session_id=session_id,
            origin=origin,
            run_id=run.id,
            events=self._events,
        )
        emit_event(
            ctx,
            "run.started",
            session_id=session_id,
            origin=origin,
            prompt_version=run.prompt_version,
        )
        return PreparedTurn(
            run=run, history=history, ctx=ctx, user_id=user_id, session_id=session_id
        )

    def run_prepared(
        self,
        prepared: PreparedTurn,
        *,
        on_token: Callable[[str], None] | None = None,
        cancel: CancellationToken | None = None,
    ) -> tuple[str, str]:
        """Execute a prepared turn, persist its messages and finish the run."""
        run, ctx = prepared.run, prepared.ctx
        session_id, user_id, origin = prepared.session_id, prepared.user_id, run.origin
        try:
            outcome = self._agent.run_turn(prepared.history, ctx, on_token=on_token, cancel=cancel)
        except Exception as exc:
            message = str(exc) if isinstance(exc, AgentError) else GENERIC_FAILURE
            self._finish(run, RunStatus.FAILED, error=message)
            emit_event(ctx, "run.failed", status="failed", error=message)
            self._record(
                "chat.turn_failed",
                user_id,
                {
                    "session_id": session_id,
                    "origin": origin,
                    "error_type": type(exc).__name__,
                },
            )
            raise
        for message_ in outcome.new_messages:
            self._conversations.append(session_id, message_)
        reply = outcome_from_agent(outcome)
        if outcome.stop_reason == "awaiting_approval":
            # APR-02: pause. The stream already ended on approval.required; the thread is
            # released and the run waits in storage until the owner decides.
            self._finish(
                run,
                RunStatus.AWAITING_APPROVAL,
                final_text=reply,
                stop_reason=outcome.stop_reason,
            )
            self._record(
                "chat.awaiting_approval",
                user_id,
                {
                    "session_id": session_id,
                    "origin": origin,
                    "run_id": run.id,
                    "approval_ids": list(outcome.approvals_requested),
                },
            )
            return session_id, reply
        status = RunStatus.CANCELLED if outcome.stop_reason == "cancelled" else RunStatus.COMPLETED
        self._finish(run, status, final_text=reply, stop_reason=outcome.stop_reason)
        if status is RunStatus.CANCELLED:
            emit_event(ctx, "run.failed", status="cancelled", reply=reply, stop_reason="cancelled")
        else:
            emit_event(
                ctx,
                "run.completed",
                session_id=session_id,
                reply=reply,
                stop_reason=outcome.stop_reason,
            )
        self._record(
            "chat.assistant_response",
            user_id,
            {
                "session_id": session_id,
                "origin": origin,
                "character_count": len(reply),
                "tool_call_count": len(outcome.tool_calls_made),
            },
        )
        return session_id, reply

    # -- pause / resume (APR-02) ---------------------------------------------

    def awaiting_run(self, run_id: str) -> AgentRun | None:
        """The run if it exists and is paused for approval, else None."""
        run = self._runs.get(run_id) if self._runs is not None else None
        return run if run is not None and run.status is RunStatus.AWAITING_APPROVAL else None

    def resume_run(
        self,
        run_id: str,
        *,
        approval_id: str,
        call_id: str,
        tool_name: str,
        output: str,
        ok: bool,
        untrusted: bool = False,
        cancel: CancellationToken | None = None,
    ) -> tuple[str, str]:
        """Continue a paused run after its approved tool executed; AURA reports the outcome."""
        run = self.awaiting_run(run_id)
        if run is None:
            raise StorageError("This run is not waiting for approval.")
        ctx = ToolContext(
            user_id=run.user_id,
            session_id=run.session_id,
            origin=run.origin,
            run_id=run.id,
            events=self._events,
            untrusted_content=untrusted,
        )
        emit_event(ctx, "approval.resolved", approval_id=approval_id, decision="approved")
        emit_event(ctx, "tool.finished", call_id=call_id, name=tool_name, ok=ok, output=output)
        self._conversations.append(
            run.session_id,
            Message(
                role="tool", content=output or "(no output)", name=tool_name, tool_call_id=call_id
            ),
        )
        run.status = RunStatus.RUNNING
        run.finished_at = None
        self._save_run(run)
        history = self._conversations.load(run.session_id, limit=self._history_limit)
        history = arrange_tool_results(omit_retired_tool_messages(history, {"noop"}))
        history = [self._system_message(run.user_id)[0], *history]
        prepared = PreparedTurn(
            run=run, history=history, ctx=ctx, user_id=run.user_id, session_id=run.session_id
        )
        return self.run_prepared(prepared, cancel=cancel)

    def conclude_declined(
        self,
        run_id: str,
        *,
        approval_id: str,
        call_id: str,
        tool_name: str,
        decision: str,
        message: str,
    ) -> str | None:
        """Finish a paused run whose action was denied or expired, and tell the owner.

        Nothing ran, so no model call is needed: the reply is deterministic.
        """
        run = self.awaiting_run(run_id)
        if run is None:
            return None
        ctx = ToolContext(
            user_id=run.user_id,
            session_id=run.session_id,
            origin=run.origin,
            run_id=run.id,
            events=self._events,
        )
        emit_event(ctx, "approval.resolved", approval_id=approval_id, decision=decision)
        emit_event(
            ctx,
            "tool.finished",
            call_id=call_id,
            name=tool_name,
            ok=False,
            output=f"Not run: approval {decision}.",
        )
        self._conversations.append(
            run.session_id,
            Message(
                role="tool",
                content=f"Not run: the owner's approval was {decision}.",
                name=tool_name,
                tool_call_id=call_id,
            ),
        )
        self._conversations.append(run.session_id, Message(role="assistant", content=message))
        self._finish(run, RunStatus.COMPLETED, final_text=message)
        emit_event(ctx, "run.completed", session_id=run.session_id, reply=message, stop_reason=None)
        self._record(
            "chat.approval_declined",
            run.user_id,
            {"run_id": run.id, "approval_id": approval_id, "decision": decision},
        )
        return message

    def _save_run(self, run: AgentRun) -> None:
        if self._runs is None:
            return
        try:
            self._runs.save(run)
        except Exception:  # noqa: BLE001 — bookkeeping failure must not break the resume
            logger.exception("Could not persist run %s", run.id)

    # -- internals -----------------------------------------------------------

    def _system_message(self, identity: str) -> tuple[Message, str]:
        profile = (
            self._profiles.get(identity) if self._profiles else OwnerProfile(owner_id=identity)
        )
        today = self._clock().astimezone(get_zone(profile.timezone)).date()
        rendered = render_system_prompt(
            today=today,
            timezone=profile.timezone,
            language=profile.language,
            owner_name=profile.name,
            facts=self._memory.recall(identity, limit=10),
        )
        return Message(role="system", content=rendered.text), rendered.version

    def _finish(
        self,
        run: AgentRun,
        status: RunStatus,
        *,
        final_text: str = "",
        error: str = "",
        stop_reason: str | None = None,
    ) -> None:
        run.status = status
        run.final_text = final_text
        run.error = error
        run.stop_reason = stop_reason
        run.finished_at = None if status is RunStatus.AWAITING_APPROVAL else self._clock()
        if self._runs is None:
            return
        try:
            self._runs.save(run)
        except Exception:  # noqa: BLE001 — a bookkeeping failure must not lose the reply
            logger.exception("Could not persist run %s", run.id)

    def _record(self, event: str, actor: str, details: dict[str, object]) -> None:
        if self._audit is not None:
            self._audit.record(event, actor, details)


def outcome_from_agent(outcome: RunOutcome) -> str:
    """Fall back to a friendly message when the model returned nothing usable."""
    if not outcome.final_text:
        logger.warning(
            "Agent turn produced empty text; %d tool calls.", len(outcome.tool_calls_made)
        )
        return "(The model returned no final text.)"
    return outcome.final_text
