"""The agent loop.

Pure orchestration: it sequences provider calls and tool executions against the
`domain.ports` Protocols. It knows no platform, no database, no provider vendor — and
it never bypasses `ToolRegistry.execute`, which is where permissions and approvals
are enforced by application code.

Each step is reported on the run's `EventSink` (`ctx.events`): `token`, `tool.started`
and `tool.finished`. Run lifecycle events (`run.started`, `run.completed`, `run.failed`)
belong to the owner of the run (`ChatService`), which knows when persistence is done.

Limits (BR-09): at most `max_tool_rounds` tool rounds and `max_seconds` wall-clock per
run. At a limit — or when the owner cancels — the loop stops *between* steps and returns
a progress summary instead of a generic failure.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence

from personal_agent.application.run_events import emit_event
from personal_agent.application.tools.selection import select_tools
from personal_agent.domain.exceptions import AgentError, RunCancelledError
from personal_agent.domain.models import (
    CancellationToken,
    Message,
    RunOutcome,
    ToolCall,
    ToolContext,
)
from personal_agent.domain.ports import ModelProvider, ToolRegistry

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOOL_ROUNDS = 6
DEFAULT_MAX_SECONDS = 90.0
SUMMARY_SNIPPET = 80


class Agent:
    """Runs the "reason → act → observe" loop until the model produces final text."""

    def __init__(
        self,
        *,
        provider: ModelProvider,
        registry: ToolRegistry,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
        max_seconds: float = DEFAULT_MAX_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._max_tool_rounds = max_tool_rounds
        self._max_seconds = max_seconds
        self._clock = clock

    def run_turn(
        self,
        history: Sequence[Message],
        ctx: ToolContext,
        on_token: Callable[[str], None] | None = None,
        cancel: CancellationToken | None = None,
    ) -> RunOutcome:
        """Complete one chat turn.

        - Sends `history` (user + prior turns) to the model along with the tool specs.
        - If the model requests tool calls, executes them through the registry gate
          (permissions, schema validation, approvals, audit) and feeds results back.
        - Stops on a final text answer, a cancel, or a BR-09 limit (with a summary).
        """
        outcome = RunOutcome(final_text="")
        convo: list[Message] = list(history)
        deadline = self._clock() + self._max_seconds

        def token(text: str) -> None:
            if cancel is not None and cancel.cancelled:
                raise RunCancelledError("The run was stopped.")
            emit_event(ctx, "token", text=text)
            if on_token is not None:
                on_token(text)

        # Streaming is only worth its cost (no replay on failure) when someone listens or
        # may need to interrupt a model call.
        stream = on_token is not None or cancel is not None

        for _round in range(self._max_tool_rounds):
            if cancel is not None and cancel.cancelled:
                return self._stop(outcome, "cancelled", [])
            if self._clock() >= deadline:
                return self._stop(outcome, "limit_time", [])
            try:
                tools = select_tools(convo, self._registry.specs())
                if stream:
                    turn = self._provider.chat(convo, tools, on_token=token)
                else:
                    turn = self._provider.chat(convo, tools)
            except RunCancelledError:
                return self._stop(outcome, "cancelled", [])
            except AgentError:
                logger.exception("Provider failed mid-turn")
                raise

            if not turn.tool_calls:
                outcome.final_text = turn.content.strip() if turn.content else turn.content
                if turn.content:
                    outcome.new_messages.append(Message(role="assistant", content=turn.content))
                return outcome

            assistant = Message(role="assistant", content=turn.content, tool_calls=turn.tool_calls)
            convo.append(assistant)
            outcome.new_messages.append(assistant)

            calls = list(turn.tool_calls)
            for index, call in enumerate(calls):
                reason = self._interrupt_reason(cancel, deadline)
                if reason is not None:
                    self._skip(calls[index:], reason, convo, outcome)
                    return self._stop(outcome, reason, calls[index:])
                self._execute_one(call, ctx, convo, outcome)

        # BR-09: round budget exhausted — summarise instead of a generic failure.
        logger.warning("Tool round budget exhausted; summarising progress.")
        return self._stop(outcome, "limit_rounds", [])

    # -- stopping ------------------------------------------------------------

    def _interrupt_reason(self, cancel: CancellationToken | None, deadline: float) -> str | None:
        if cancel is not None and cancel.cancelled:
            return "cancelled"
        if self._clock() >= deadline:
            return "limit_time"
        return None

    @staticmethod
    def _skip(calls: Sequence[ToolCall], reason: str, convo: list[Message], o: RunOutcome) -> None:
        """Keep the transcript valid: every requested call gets a tool message."""
        note = (
            "Not run: the owner stopped this run."
            if reason == "cancelled"
            else "Not run: the time limit for this run was reached."
        )
        for call in calls:
            message = Message(role="tool", content=note, name=call.name, tool_call_id=call.id)
            convo.append(message)
            o.new_messages.append(message)

    def _stop(self, outcome: RunOutcome, reason: str, unrun: Sequence[ToolCall]) -> RunOutcome:
        outcome.stop_reason = reason
        outcome.final_text = self._progress_summary(outcome, reason, unrun)
        outcome.new_messages.append(Message(role="assistant", content=outcome.final_text))
        return outcome

    def _progress_summary(self, outcome: RunOutcome, reason: str, unrun: Sequence[ToolCall]) -> str:
        """What is finished, what remains, and what to do next (AGT-04)."""
        why = {
            "cancelled": "I stopped because you asked me to.",
            "limit_rounds": (
                f"I stopped after {self._max_tool_rounds} tool rounds, which is the limit "
                "for one request."
            ),
            "limit_time": (
                f"I stopped after {self._max_seconds:g} seconds, which is the limit "
                "for one request."
            ),
        }[reason]
        results = {m.tool_call_id: m for m in outcome.new_messages if m.role == "tool"}
        done = []
        for call in outcome.tool_calls_made:
            result = results.get(call.id)
            snippet = (result.content if result else "").strip().replace("\n", " ")
            snippet = snippet[:SUMMARY_SNIPPET] + "…" if len(snippet) > SUMMARY_SNIPPET else snippet
            done.append(f"- {call.name}" + (f": {snippet}" if snippet else ""))
        failed = [
            m for m in results.values() if m.tool_call_id not in _ids(outcome.tool_calls_made)
        ]
        lines = [why, ""]
        lines.append("Done so far:" if done else "Done so far: nothing yet.")
        lines.extend(done)
        remaining = [f"- {call.name} (not run)" for call in unrun]
        remaining.extend(
            f"- {m.name} (could not run: {m.content[:SUMMARY_SNIPPET]})"
            for m in failed
            if m.content and not m.content.startswith("Not run:")
        )
        lines.append("")
        lines.append("Still to do:")
        lines.extend(remaining or ["- Finish your request using the results above."])
        if reason != "cancelled":
            lines.append("")
            lines.append("Tell me to continue and I will pick up from here.")
        return "\n".join(lines)

    # -- tools ---------------------------------------------------------------

    def _execute_one(
        self,
        call: ToolCall,
        ctx: ToolContext,
        convo: list[Message],
        outcome: RunOutcome,
    ) -> None:
        """Execute one tool call; failures become tool messages the model can react to."""
        emit_event(
            ctx, "tool.started", call_id=call.id, name=call.name, arguments=dict(call.arguments)
        )
        started = time.monotonic()
        try:
            result = self._registry.execute(call, ctx)
            content, ok = result.output if result.ok else result.error or "tool failed", result.ok
        except AgentError as exc:
            logger.warning("Tool '%s' blocked: %s", call.name, exc)
            content, ok = str(exc), False
        emit_event(
            ctx,
            "tool.finished",
            call_id=call.id,
            name=call.name,
            ok=ok,
            output=content,
            duration_ms=int((time.monotonic() - started) * 1000),
        )

        message = Message(role="tool", content=content, name=call.name, tool_call_id=call.id)
        convo.append(message)
        outcome.new_messages.append(message)
        if not ok:
            outcome.final_text = outcome.final_text or (
                f"Tool '{call.name}' could not run: {content}"
            )
        else:
            outcome.tool_calls_made.append(call)


def _ids(calls: Sequence[ToolCall]) -> set[str]:
    return {call.id for call in calls}
