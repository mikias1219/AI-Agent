"""Offline fake provider — makes the whole system runnable without Ollama.

Used by every unit/integration/e2e/security test and by `PERSONAL_AGENT_PROVIDER=fake`
development sessions. It hands back pre-scripted turns in order; when the script is
empty it answers "Okay." Keeping this deterministic (no randomness) keeps tests stable.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from personal_agent.domain.models import (
    AssistantTurn,
    Message,
    ToolContext,
    ToolSpec,
)


class FakeProvider:
    """`domain.ports.ModelProvider` implementation backed by a scripted response list."""

    def __init__(self, script: Sequence[str | AssistantTurn] = ()) -> None:
        self._script = list(script)
        self.calls: list[tuple[list[Message], int]] = []

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        on_token: Callable[[str], None] | None = None,
    ) -> AssistantTurn:
        self.calls.append((list(messages), len(tools)))
        item = self._script.pop(0) if self._script else AssistantTurn(content="Okay.")
        turn = item if isinstance(item, AssistantTurn) else AssistantTurn(content=item)
        if on_token and turn.content:
            on_token(turn.content)
        return turn

    # (ToolContext is imported for parity with the Protocol shape, never used here.)
    def last_tool_count(self) -> int:
        if not self.calls:
            return 0
        return self.calls[-1][1]

    def describe_tool_context(self, ctx: ToolContext) -> str:
        """Optional debug helper for tests/e2e traces showing tool origin."""
        return f"user={ctx.user_id} session={ctx.session_id} origin={ctx.origin}"
