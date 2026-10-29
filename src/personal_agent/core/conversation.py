"""Conversation assembly, independent of any provider wire format.

The service layer composes *what* to say; this module provides helpers for
*how conversation context is assembled*: preferences from memory, plus the
persisted history from the ConversationRepository. It contains no DB or vendor code.
"""

from __future__ import annotations

from collections.abc import Sequence

from personal_agent.core.ports import MemoryStore
from personal_agent.core.types import Message


def build_system_context(
    user_id: str,
    memory: MemoryStore,
    max_facts: int = 10,
) -> Message | None:
    """Inject long-lived personal context (preferences/facts) as a system message."""
    facts = memory.recall(user_id, limit=max_facts)
    if not facts:
        return None
    lines = "\n".join(f"- {fact}" for fact in facts)
    return Message(
        role="system",
        content=f"Known preferences and facts about this user:\n{lines}",
    )


def wrap_tool_output(output: str) -> str:
    """Ensure tool outputs are non-empty strings for round-tripping back to a model."""
    return output or "(no output)"


def summarize_history(messages: Sequence[Message], limit: int = 6) -> str:
    """Human-readable short transcript for logs and debugging traces."""
    lines = []
    for message in messages[-limit:]:
        tag = message.role + (f"/{message.name}" if message.name else "")
        lines.append(f"{tag}: {message.content}")
    return "\n".join(lines)
