"""SQLAlchemy repository for time entries."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.timetrack import TimeEntry
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import TimeEntryRow

_FIELDS = (
    "owner_user_id",
    "task_id",
    "goal_id",
    "project",
    "started_at",
    "ended_at",
    "note",
    "source",
)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _entry(row: TimeEntryRow) -> TimeEntry:
    return TimeEntry(
        id=row.id,
        owner_user_id=row.owner_user_id,
        started_at=_aware(row.started_at),  # type: ignore[arg-type]
        ended_at=_aware(row.ended_at),
        task_id=row.task_id,
        goal_id=row.goal_id,
        project=row.project or "",
        note=row.note or "",
        source=row.source,
    )


class TimeRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, entry: TimeEntry) -> None:
        with session_scope(self._factory) as s:
            row = TimeEntryRow(id=entry.id)
            for name in _FIELDS:
                setattr(row, name, getattr(entry, name))
            s.add(row)

    def get(self, owner: str, entry_id: str) -> TimeEntry | None:
        with session_scope(self._factory) as s:
            row = s.get(TimeEntryRow, entry_id)
            return _entry(row) if row and row.owner_user_id == owner else None

    def save(self, entry: TimeEntry) -> None:
        with session_scope(self._factory) as s:
            row = s.get(TimeEntryRow, entry.id)
            if row is not None:
                for name in _FIELDS:
                    setattr(row, name, getattr(entry, name))

    def delete(self, owner: str, entry_id: str) -> bool:
        with session_scope(self._factory) as s:
            row = s.get(TimeEntryRow, entry_id)
            if row is None or row.owner_user_id != owner:
                return False
            s.delete(row)
            return True

    def running(self, owner: str) -> TimeEntry | None:
        with session_scope(self._factory) as s:
            row = s.scalars(
                select(TimeEntryRow)
                .where(TimeEntryRow.owner_user_id == owner, TimeEntryRow.ended_at.is_(None))
                .order_by(TimeEntryRow.started_at.desc())
            ).first()
            return _entry(row) if row else None

    def between(self, owner: str, start: datetime, end: datetime) -> Sequence[TimeEntry]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(TimeEntryRow)
                .where(
                    TimeEntryRow.owner_user_id == owner,
                    TimeEntryRow.started_at >= start,
                    TimeEntryRow.started_at < end,
                )
                .order_by(TimeEntryRow.started_at.desc())
            )
            return [_entry(r) for r in rows]
