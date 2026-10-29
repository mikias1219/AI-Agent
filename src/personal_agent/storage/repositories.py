"""Repository implementations of the `core.ports` contracts.

Each repository owns its SQL and its mapping to `core/types.py` — no other layer
constructs or queries ORM rows.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from personal_agent.core.errors import StorageError
from personal_agent.core.types import (
    Message,
    Task,
    TaskStatus,
    ToolCall,
    ToolContext,
)
from personal_agent.storage.db import session_scope
from personal_agent.storage.models import (
    ApprovalRow,
    AuditEntryRow,
    ConversationRow,
    MessageRow,
    TaskRow,
)

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_LIMIT = 20


# -- conversations -----------------------------------------------------------


class ConversationRepositoryImpl:
    """Implements `core.ports.ConversationRepository` over SQLAlchemy."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create_session(self, user_id: str) -> str:
        """Persist and return a new conversation id."""
        session_id = uuid.uuid4().hex
        with session_scope(self._factory) as session:
            session.add(ConversationRow(id=session_id, user_id=user_id))
        return session_id

    def append(self, session_id: str, message: Message) -> None:
        """Append one domain message, serializing provider tool calls to JSON."""
        with session_scope(self._factory) as session:
            session.add(
                MessageRow(
                    conversation_id=session_id,
                    role=message.role,
                    content=message.content,
                    name=message.name,
                    tool_call_id=message.tool_call_id,
                    tool_calls_json=json.dumps(
                        [
                            {"id": c.id, "name": c.name, "arguments": c.arguments}
                            for c in message.tool_calls
                        ]
                    ),
                )
            )

    def load(self, session_id: str, limit: int = DEFAULT_HISTORY_LIMIT) -> list[Message]:
        """Load recent history oldest→newest; empty list for unknown sessions."""
        with session_scope(self._factory) as session:
            rows = (
                session.query(MessageRow)
                .filter(MessageRow.conversation_id == session_id)
                .order_by(MessageRow.id.desc())
                .limit(limit)
                .all()
            )
        rows.reverse()
        return [_message_from_row(row) for row in rows]


def _message_from_row(row: MessageRow) -> Message:
    try:
        raw_calls = json.loads(row.tool_calls_json or "[]")
    except ValueError:
        logger.warning("Skipped malformed tool_calls_json on message id=%s", row.id)
        raw_calls = []
    calls = tuple(
        ToolCall(
            id=str(c.get("id", "")),
            name=str(c.get("name", "")),
            arguments=c.get("arguments") or {},
        )
        for c in raw_calls
        if isinstance(c, dict)
    )
    return Message(
        role=row.role,  # type: ignore[arg-type]  # roles are constrained at write time
        content=row.content,
        name=row.name,
        tool_call_id=row.tool_call_id,
        tool_calls=calls,
    )


# -- tasks -------------------------------------------------------------------


class TaskRepositoryImpl:
    """Implements `core.ports.TaskRepository` over SQLAlchemy."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, task: Task) -> None:
        """Persist a fresh task."""
        with session_scope(self._factory) as session:
            session.add(TaskRow(**_task_to_row_fields(task)))

    def get(self, task_id: str) -> Task | None:
        """Fetch one task or None — 'not found' is a normal result."""
        with session_scope(self._factory) as session:
            row = session.get(TaskRow, task_id)
            return _task_from_row(row) if row else None

    def list(self, status: TaskStatus | None = None) -> list[Task]:
        """List tasks, optional status filter, newest first."""
        with session_scope(self._factory) as session:
            query = session.query(TaskRow).order_by(TaskRow.created_at.desc())
            if status is not None:
                query = query.filter(TaskRow.status == status.value)
            return [_task_from_row(row) for row in query.all()]

    def save(self, task: Task) -> None:
        """Update an existing task's mutable fields (status, title, ...)."""
        fields = _task_to_row_fields(task)
        with session_scope(self._factory) as session:
            row = session.get(TaskRow, task.id)
            if row is None:
                raise StorageError(f"Cannot save unknown task id={task.id}.")
            for key, value in fields.items():
                setattr(row, key, value)


def _task_to_row_fields(task: Task) -> dict[str, Any]:
    """Domain → column mapping, shared by add() and save()."""
    return {
        "id": task.id,
        "owner_user_id": task.owner_user_id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _task_from_row(row: TaskRow) -> Task:
    """Column → domain mapping."""
    return Task(
        id=row.id,
        title=row.title,
        description=row.description,
        status=TaskStatus(row.status),
        owner_user_id=row.owner_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# -- approvals (implements the protocol declared in security/approvals) ------


class ApprovalRepositoryImpl:
    """Implements the `ApprovalRepository` Protocol from `security/approvals.py`."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create_pending(self, approval_id: str, call: ToolCall, ctx: ToolContext) -> None:
        """Persist a fresh pending approval row."""
        with session_scope(self._factory) as session:
            session.add(
                ApprovalRow(
                    id=approval_id,
                    tool_name=call.name,
                    arguments_json=json.dumps(call.arguments),
                    user_id=ctx.user_id,
                    session_id=ctx.session_id,
                    origin=ctx.origin,
                    status="pending",
                )
            )

    def decision(self, approval_id: str) -> str | None:
        """Current status of a request: pending | approved | denied | None."""
        with session_scope(self._factory) as session:
            row = session.get(ApprovalRow, approval_id)
            return row.status if row else None

    def update_status(self, approval_id: str, status: str) -> None:
        """Set 'approved' or 'denied', stamping decided_at."""
        with session_scope(self._factory) as session:
            row = session.get(ApprovalRow, approval_id)
            if row is None:
                raise StorageError(f"Unknown approval id={approval_id[:8]}.")
            row.status = status
            row.decided_at = datetime.now(UTC)


# -- audit log ---------------------------------------------------------------


class AuditLogImpl:
    """Append-only implementation of `core.ports.AuditLog`."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def record(self, event: str, actor: str, details: dict[str, Any]) -> None:
        """Append one row; auditing must never crash the caller's flow."""
        try:
            with session_scope(self._factory) as session:
                session.add(AuditEntryRow(actor=actor, event=event, details_json=details))
        except Exception:  # noqa: BLE001 — audit must never take the app down
            logger.exception("Failed to persist audit event '%s'", event)


def recent_audit(factory: sessionmaker[Session], limit: int = 50) -> list[AuditEntryRow]:
    """Read-side helper for debugging/monitoring (used by future ops tooling)."""
    with session_scope(factory) as session:
        return session.query(AuditEntryRow).order_by(AuditEntryRow.id.desc()).limit(limit).all()
