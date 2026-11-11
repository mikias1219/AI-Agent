"""Conversation assembly, independent of any provider wire format.

The service layer composes *what* to say; this module provides helpers for
*how conversation context is assembled* from the persisted history of the
ConversationRepository (the system prompt itself lives in `personal_agent.prompts`).
It contains no DB or vendor code.
"""

from __future__ import annotations

from collections.abc import Sequence

from personal_agent.domain.models import Message


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


def omit_retired_tool_messages(messages: Sequence[Message], retired: set[str]) -> list[Message]:
    """Keep saved history intact while dropping obsolete tool traffic from model input."""
    retired_ids = {
        call.id for message in messages for call in message.tool_calls if call.name in retired
    }
    result = []
    for message in messages:
        if message.role == "tool" and (
            message.name in retired or message.tool_call_id in retired_ids
        ):
            continue
        if message.tool_calls:
            calls = tuple(call for call in message.tool_calls if call.name not in retired)
            if calls or message.content:
                result.append(
                    Message(
                        role=message.role,
                        content=message.content,
                        name=message.name,
                        tool_call_id=message.tool_call_id,
                        tool_calls=calls,
                    )
                )
        else:
            result.append(message)
    return result
