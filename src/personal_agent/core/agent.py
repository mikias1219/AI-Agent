"""The agent loop.

Pure orchestration: it sequences provider calls and tool executions against the
`core.ports` Protocols. It knows no platform, no database, no provider vendor — and
it never bypasses `ToolRegistry.execute`, which is where permissions and approvals
are enforced by application code.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from personal_agent.core.errors import AgentError
from personal_agent.core.ports import ModelProvider, ToolRegistry
from personal_agent.core.types import (
    Message,
    RunOutcome,
    ToolCall,
    ToolContext,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOOL_ROUNDS = 5


class Agent:
    """Runs the "reason → act → observe" loop until the model produces final text."""

    def __init__(
        self,
        *,
        provider: ModelProvider,
        registry: ToolRegistry,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._max_tool_rounds = max_tool_rounds

    def run_turn(self, history: Sequence[Message], ctx: ToolContext) -> RunOutcome:
        """Complete one chat turn.

        - Sends `history` (user + prior turns) to the model along with the tool specs.
        - If the model requests tool calls, executes them through the registry gate
          (permissions, schema validation, approvals, audit) and feeds results back.
        - Stops on a final text answer or when the round budget is exhausted.
        """
        outcome = RunOutcome(final_text="")
        convo: list[Message] = list(history)

        for _round in range(self._max_tool_rounds):
            try:
                turn = self._provider.chat(convo, self._registry.specs())
            except AgentError:
                logger.exception("Provider failed mid-turn")
                raise

            if not turn.tool_calls:
                outcome.final_text = turn.content.strip() if turn.content else turn.content
                if turn.content:
                    outcome.new_messages.append(Message(role="assistant", content=turn.content))
                return outcome

            convo.append(
                Message(role="assistant", content=turn.content, tool_calls=turn.tool_calls),
            )
            outcome.new_messages.append(
                Message(role="assistant", content=turn.content, tool_calls=turn.tool_calls),
            )

            for call in turn.tool_calls:
                self._execute_one(call, ctx, convo, outcome)

        # Round budget exhausted: stop trusting the loop and end the turn early.
        logger.warning("Tool round budget exhausted; ending turn politely.")
        outcome.final_text = "I stopped early: too many tool actions in one turn. Please retry."
        outcome.new_messages.append(Message(role="assistant", content=outcome.final_text))
        return outcome

    def _execute_one(
        self,
        call: ToolCall,
        ctx: ToolContext,
        convo: list[Message],
        outcome: RunOutcome,
    ) -> None:
        """Execute one tool call; failures become tool messages the model can react to."""
        try:
            result = self._registry.execute(call, ctx)
            content, ok = result.output if result.ok else result.error or "tool failed", result.ok
        except AgentError as exc:
            logger.warning("Tool '%s' blocked: %s", call.name, exc)
            content, ok = str(exc), False

        message = Message(role="tool", content=content, name=call.name, tool_call_id=call.id)
        convo.append(message)
        outcome.new_messages.append(message)
        if not ok:
            outcome.final_text = outcome.final_text or (
                f"Tool '{call.name}' could not run: {content}"
            )
        else:
            outcome.tool_calls_made.append(call)
