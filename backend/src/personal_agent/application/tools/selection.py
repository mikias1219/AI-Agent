"""Avoid unnecessary built-in tool rounds for clearly informational English questions.

Ambiguous/action requests and other languages keep the full tool set. Unknown/custom
integrations always remain available. This selects context, never grants permission.
"""

import re
from collections.abc import Sequence

from personal_agent.domain.models import Message, ToolSpec

_BUILTINS = {"get_current_datetime", "task_create", "task_list", "task_update_status"}
_INFORMATIONAL = re.compile(
    r"^(hi\b|hello\b|hey\b|thanks\b|thank you\b|what (is|are|can)\b|who (is|are)\b|"
    r"why\b|how (does|do|can)\b|explain\b|define\b|tell me about\b|can you explain\b)",
    re.I,
)
_OPERATIONAL = re.compile(
    r"\b(task\w*|todo|to-do|remind\w*|time|date|today|tomorrow|yesterday|clock|"
    r"create|add|update|mark|finish|cancel|complete|save|delete|remove|schedule|"
    r"send|post|publish|search|check|fetch)\b",
    re.I,
)
_REFERENCES = re.compile(r"\b(it|that|those|them|they|this|same|another)\b", re.I)


def select_tools(history: Sequence[Message], tools: Sequence[ToolSpec]) -> list[ToolSpec]:
    latest = next((m.content.strip() for m in reversed(history) if m.role == "user"), "")
    if (
        not latest.isascii()
        or not _INFORMATIONAL.search(latest)
        or _OPERATIONAL.search(latest)
        or _REFERENCES.search(latest)
    ):
        return list(tools)
    return [tool for tool in tools if tool.name not in _BUILTINS]
