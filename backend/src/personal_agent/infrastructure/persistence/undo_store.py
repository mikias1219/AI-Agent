"""SQLAlchemy-backed undo window records (AG-TRU-04)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.undo import UndoAction
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import UndoActionRow


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _from_row(row: UndoActionRow) -> UndoAction:
    return UndoAction(
        id=row.id,
        owner_user_id=row.owner_user_id,
        tool_name=row.tool_name,
        summary=row.summary or "",
        entity_id=row.entity_id or "",
        payload=dict(row.payload_json or {}),
        status=row.status,
        created_at=_aware(row.created_at),
        expires_at=_aware(row.expires_at),
        undone_at=_aware(row.undone_at),
    )


def _apply(row: UndoActionRow, action: UndoAction) -> None:
    row.tool_name = action.tool_name
    row.summary = action.summary
    row.entity_id = action.entity_id
    row.payload_json = dict(action.payload)
    row.status = action.status
    row.expires_at = action.expires_at
    row.undone_at = action.undone_at
    if action.created_at is not None:
        row.created_at = action.created_at


class UndoStoreImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, action: UndoAction) -> None:
        row = UndoActionRow(id=action.id, owner_user_id=action.owner_user_id)
        _apply(row, action)
        with session_scope(self._factory) as session:
            session.add(row)

    def get(self, undo_id: str) -> UndoAction | None:
        with session_scope(self._factory) as session:
            row = session.get(UndoActionRow, undo_id)
            return _from_row(row) if row else None

    def save(self, action: UndoAction) -> None:
        with session_scope(self._factory) as session:
            row = session.get(UndoActionRow, action.id)
            if row is None:
                raise StorageError(f"Unknown undo '{action.id}'.")
            _apply(row, action)

    def list_open(self, owner_user_id: str, *, limit: int = 50) -> list[UndoAction]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(UndoActionRow)
                .filter(
                    UndoActionRow.owner_user_id == owner_user_id,
                    UndoActionRow.status == "open",
                )
                .order_by(UndoActionRow.created_at.desc())
                .limit(limit)
                .all()
            )
            return [_from_row(r) for r in rows]
