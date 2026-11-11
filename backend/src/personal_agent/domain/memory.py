"""Memory kinds, records, and redaction (MEM-01, MEM-06, BR-08)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

MemoryKind = Literal["preference", "fact", "person", "routine"]
MEMORY_KINDS: frozenset[str] = frozenset({"preference", "fact", "person", "routine"})

# Card numbers (13–19 digits with optional separators), SSN-like, common secret labels.
_CARD = re.compile(r"(?:\d[ -]*?){13,19}")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_SECRET_LABEL = re.compile(
    r"(?i)\b(password|passwd|api[_\s-]?key|secret[_\s-]?key|private[_\s-]?key|"
    r"bearer\s+[a-z0-9._\-]+|sk-[a-z0-9]{16,}|AIza[0-9A-Za-z\-_]{20,})\b"
)
_GOV_ID = re.compile(
    r"(?i)\b(passport|national\s*id|driver'?s?\s*licen[cs]e|ssn|social\s*security)\b"
    r".{0,40}\b[A-Z0-9]{5,}\b"
)


@dataclass(slots=True)
class Memory:
    """One owner-controlled memory item."""

    id: str
    user_id: str
    kind: MemoryKind
    content: str
    source_run_id: str | None = None
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    deleted_at: datetime | None = None


def normalize_kind(raw: str) -> MemoryKind:
    kind = (raw or "fact").strip().lower()
    if kind not in MEMORY_KINDS:
        raise ValueError(f"Unknown memory kind '{raw}'. Use preference, fact, person, or routine.")
    return kind  # type: ignore[return-value]


def redaction_reason(content: str) -> str | None:
    """Return a refusal reason if content must not be stored; else None."""
    text = content.strip()
    if not text:
        return "Memory content is empty."
    if _CARD.search(text.replace(" ", "")) or _CARD.search(text):
        digits = re.sub(r"\D", "", text)
        if len(digits) >= 13:
            return "Payment card numbers cannot be stored in memory."
    if _SSN.search(text):
        return "Government ID numbers cannot be stored in memory."
    if _SECRET_LABEL.search(text):
        return "Credentials and API secrets cannot be stored in memory."
    if _GOV_ID.search(text):
        return "Government ID details cannot be stored in memory."
    return None


def assert_storable(content: str) -> str:
    reason = redaction_reason(content)
    if reason:
        raise ValueError(reason)
    return content.strip()


__all__ = [
    "MEMORY_KINDS",
    "Memory",
    "MemoryKind",
    "assert_storable",
    "normalize_kind",
    "redaction_reason",
]
