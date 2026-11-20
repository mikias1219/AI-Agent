"""Reversible auto-run records for the Balanced undo window (AG-TRU-04)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

UNDO_WINDOW = timedelta(minutes=10)

# Tools that can be reversed within the undo window.
REVERSIBLE_TOOLS: frozenset[str] = frozenset(
    {
        "task_create",
        "reminder_create",
        "google_calendar_create",
        "google_gmail_create_draft",
    }
)

# Execute tools Balanced may skip approval for (ceilings still apply elsewhere).
BALANCED_AUTO_EXECUTE: frozenset[str] = frozenset({"google_calendar_create"})


@dataclass(slots=True)
class UndoAction:
    id: str
    owner_user_id: str
    tool_name: str
    summary: str = ""
    entity_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "open"  # open | undone | expired
    created_at: datetime | None = None
    expires_at: datetime | None = None
    undone_at: datetime | None = None


__all__ = [
    "BALANCED_AUTO_EXECUTE",
    "REVERSIBLE_TOOLS",
    "UNDO_WINDOW",
    "UndoAction",
]
