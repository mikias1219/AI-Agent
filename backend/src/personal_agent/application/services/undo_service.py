"""10-minute undo window for Balanced auto-runs (AG-TRU-04)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.exceptions import AgentError, StorageError
from personal_agent.domain.ports import AuditLog, UndoStore
from personal_agent.domain.undo import (
    BALANCED_AUTO_EXECUTE,
    REVERSIBLE_TOOLS,
    UNDO_WINDOW,
    UndoAction,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UndoResult:
    id: str
    summary: str
    undone: bool


class UndoService:
    def __init__(
        self,
        store: UndoStore,
        *,
        tasks: TaskService,
        cancel_reminder: Callable[[str, str], Any] | None = None,
        delete_calendar_event: Callable[[str], None] | None = None,
        delete_gmail_draft: Callable[[str], None] | None = None,
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._tasks = tasks
        self._cancel_reminder = cancel_reminder
        self._delete_calendar = delete_calendar_event
        self._delete_draft = delete_gmail_draft
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    def record(
        self,
        owner_user_id: str,
        *,
        tool_name: str,
        summary: str,
        entity_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> UndoAction | None:
        if tool_name not in REVERSIBLE_TOOLS:
            return None
        if not entity_id:
            return None
        now = self._clock()
        action = UndoAction(
            id=uuid.uuid4().hex,
            owner_user_id=owner_user_id,
            tool_name=tool_name,
            summary=(summary or tool_name)[:240],
            entity_id=entity_id,
            payload=dict(payload or {}),
            status="open",
            created_at=now,
            expires_at=now + UNDO_WINDOW,
        )
        self._store.add(action)
        if self._audit is not None:
            self._audit.record(
                "undo.recorded",
                owner_user_id,
                {"undo_id": action.id, "tool": tool_name, "entity_id": entity_id},
            )
        return action

    def list_open(self, owner_user_id: str) -> list[dict[str, Any]]:
        now = self._clock()
        open_rows = []
        for row in self._store.list_open(owner_user_id):
            expires = row.expires_at
            if expires is None or expires <= now:
                row.status = "expired"
                self._store.save(row)
                continue
            open_rows.append(self._payload(row))
        return open_rows

    def undo(self, undo_id: str, owner_user_id: str) -> UndoResult:
        row = self._store.get(undo_id)
        if row is None or row.owner_user_id != owner_user_id:
            raise StorageError(f"Unknown undo '{undo_id}'.")
        now = self._clock()
        if row.status != "open":
            raise AgentError(f"This undo is already {row.status}.")
        if row.expires_at is None or row.expires_at <= now:
            row.status = "expired"
            self._store.save(row)
            raise AgentError("The undo window has expired.")
        self._reverse(row)
        row.status = "undone"
        row.undone_at = now
        self._store.save(row)
        if self._audit is not None:
            self._audit.record(
                "undo.applied",
                owner_user_id,
                {"undo_id": row.id, "tool": row.tool_name, "entity_id": row.entity_id},
            )
        return UndoResult(id=row.id, summary=f"Undid: {row.summary}", undone=True)

    def _reverse(self, row: UndoAction) -> None:
        if row.tool_name == "task_create":
            self._tasks.soft_delete(row.entity_id)
            return
        if row.tool_name == "reminder_create":
            if self._cancel_reminder is None:
                raise AgentError("Reminders cannot be undone right now.")
            cancelled = self._cancel_reminder(row.entity_id, row.owner_user_id)
            if cancelled is None:
                raise AgentError("Reminder was not found.")
            return
        if row.tool_name == "google_calendar_create":
            if self._delete_calendar is None:
                raise AgentError("Calendar undo is unavailable (Google not connected).")
            self._delete_calendar(row.entity_id)
            return
        if row.tool_name == "google_gmail_create_draft":
            if self._delete_draft is None:
                raise AgentError("Draft undo is unavailable (Google not connected).")
            self._delete_draft(row.entity_id)
            return
        raise AgentError(f"No undo path for '{row.tool_name}'.")

    @staticmethod
    def _payload(row: UndoAction) -> dict[str, Any]:
        return {
            "id": row.id,
            "tool_name": row.tool_name,
            "summary": row.summary,
            "entity_id": row.entity_id,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        }


__all__ = [
    "BALANCED_AUTO_EXECUTE",
    "REVERSIBLE_TOOLS",
    "UNDO_WINDOW",
    "UndoResult",
    "UndoService",
]
