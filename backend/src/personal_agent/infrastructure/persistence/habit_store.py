"""SQLAlchemy repository for habits and check-ins."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.habits import Habit, HabitCheckin
from personal_agent.domain.recurrence import parse_rule
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import HabitCheckinRow, HabitRow


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _habit(row: HabitRow) -> Habit:
    return Habit(
        id=row.id,
        owner_user_id=row.owner_user_id,
        name=row.name,
        rule=parse_rule(row.rule or {}),
        kind=row.kind,
        target_value=row.target_value,
        target_unit=row.target_unit or "",
        icon=row.icon or "",
        archived=bool(row.archived),
        counts_toward_score=bool(row.counts_toward_score),
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
    )


def _checkin(row: HabitCheckinRow) -> HabitCheckin:
    return HabitCheckin(
        id=row.id,
        habit_id=row.habit_id,
        owner_user_id=row.owner_user_id,
        day=row.day,
        status=row.status,
        value=row.value,
        note=row.note or "",
        created_at=_aware(row.created_at),
    )


def _fill(row: HabitRow, habit: Habit) -> None:
    row.owner_user_id = habit.owner_user_id
    row.name = habit.name
    row.kind = habit.kind
    row.rule = habit.rule.to_dict()
    row.target_value = habit.target_value
    row.target_unit = habit.target_unit
    row.icon = habit.icon
    row.archived = habit.archived
    row.counts_toward_score = habit.counts_toward_score
    row.created_at = habit.created_at or datetime.now(UTC)
    row.updated_at = habit.updated_at or datetime.now(UTC)


class HabitRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, habit: Habit) -> None:
        with session_scope(self._factory) as s:
            row = HabitRow(id=habit.id)
            _fill(row, habit)
            s.add(row)

    def get(self, owner: str, habit_id: str) -> Habit | None:
        with session_scope(self._factory) as s:
            row = s.get(HabitRow, habit_id)
            return _habit(row) if row and row.owner_user_id == owner else None

    def save(self, habit: Habit) -> None:
        with session_scope(self._factory) as s:
            row = s.get(HabitRow, habit.id)
            if row is not None:
                _fill(row, habit)

    def list(self, owner: str, *, include_archived: bool = False) -> Sequence[Habit]:
        with session_scope(self._factory) as s:
            stmt = select(HabitRow).where(HabitRow.owner_user_id == owner)
            if not include_archived:
                stmt = stmt.where(HabitRow.archived.is_(False))
            return [_habit(r) for r in s.scalars(stmt.order_by(HabitRow.created_at, HabitRow.id))]

    def upsert_checkin(self, checkin: HabitCheckin) -> HabitCheckin:
        with session_scope(self._factory) as s:
            row = s.scalars(
                select(HabitCheckinRow).where(
                    HabitCheckinRow.habit_id == checkin.habit_id,
                    HabitCheckinRow.day == checkin.day,
                )
            ).first()
            if row is None:
                row = HabitCheckinRow(id=checkin.id, habit_id=checkin.habit_id)
                s.add(row)
            row.owner_user_id = checkin.owner_user_id
            row.day = checkin.day
            row.status = checkin.status
            row.value = checkin.value
            row.note = checkin.note
            row.created_at = checkin.created_at or datetime.now(UTC)
            s.flush()
            return _checkin(row)

    def delete_checkin(self, owner: str, habit_id: str, day: date) -> bool:
        with session_scope(self._factory) as s:
            row = s.scalars(
                select(HabitCheckinRow).where(
                    HabitCheckinRow.habit_id == habit_id,
                    HabitCheckinRow.day == day,
                    HabitCheckinRow.owner_user_id == owner,
                )
            ).first()
            if row is None:
                return False
            s.delete(row)
            return True

    def checkins(
        self, owner: str, *, start: date, end: date, habit_id: str | None = None
    ) -> Sequence[HabitCheckin]:
        with session_scope(self._factory) as s:
            stmt = select(HabitCheckinRow).where(
                HabitCheckinRow.owner_user_id == owner,
                HabitCheckinRow.day >= start,
                HabitCheckinRow.day <= end,
            )
            if habit_id:
                stmt = stmt.where(HabitCheckinRow.habit_id == habit_id)
            return [_checkin(r) for r in s.scalars(stmt.order_by(HabitCheckinRow.day))]
