"""Reminder and automation persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.scheduler import Automation, Reminder, ReminderStatus
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import AutomationRow, ReminderRow


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _reminder(row: ReminderRow) -> Reminder:
    return Reminder(
        id=row.id,
        owner_user_id=row.owner_user_id,
        text=row.text,
        remind_at=_aware(row.remind_at) or row.remind_at,
        task_id=row.task_id,
        channels=list(row.channels or ["inbox"]),
        status=ReminderStatus(row.status),
        late=bool(row.late),
        delivered_at=_aware(row.delivered_at),
        created_at=_aware(row.created_at),
    )


def _automation(row: AutomationRow) -> Automation:
    return Automation(
        id=row.id,
        owner_user_id=row.owner_user_id,
        kind=row.kind,
        enabled=bool(row.enabled),
        schedule_time=row.schedule_time or "08:00",
        channels=list(row.channels or ["inbox", "telegram"]),
        last_run_at=row.last_run_at,
        last_result=row.last_result or "",
        last_run_id=row.last_run_id,
        created_at=row.created_at,
    )


class ReminderStoreImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, reminder: Reminder) -> None:
        with session_scope(self._factory) as session:
            session.add(
                ReminderRow(
                    id=reminder.id,
                    owner_user_id=reminder.owner_user_id,
                    text=reminder.text,
                    remind_at=reminder.remind_at,
                    task_id=reminder.task_id,
                    channels=list(reminder.channels),
                    status=reminder.status.value,
                    late=1 if reminder.late else 0,
                    delivered_at=reminder.delivered_at,
                    created_at=reminder.created_at or _now(),
                )
            )

    def get(self, reminder_id: str) -> Reminder | None:
        with session_scope(self._factory) as session:
            row = session.get(ReminderRow, reminder_id)
            return _reminder(row) if row else None

    def list(
        self,
        owner_user_id: str,
        *,
        status: ReminderStatus | None = None,
        limit: int = 50,
    ) -> list[Reminder]:
        with session_scope(self._factory) as session:
            q = session.query(ReminderRow).filter(ReminderRow.owner_user_id == owner_user_id)
            if status is not None:
                q = q.filter(ReminderRow.status == status.value)
            rows = q.order_by(ReminderRow.remind_at.desc()).limit(max(1, limit)).all()
            return [_reminder(row) for row in rows]

    def save(self, reminder: Reminder) -> None:
        with session_scope(self._factory) as session:
            row = session.get(ReminderRow, reminder.id)
            if row is None:
                return
            row.text = reminder.text
            row.remind_at = reminder.remind_at
            row.task_id = reminder.task_id
            row.channels = list(reminder.channels)
            row.status = reminder.status.value
            row.late = 1 if reminder.late else 0
            row.delivered_at = reminder.delivered_at

    def due(self, now: datetime, *, limit: int = 50) -> list[Reminder]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(ReminderRow)
                .filter(
                    ReminderRow.status == ReminderStatus.PENDING.value,
                    ReminderRow.remind_at <= now,
                )
                .order_by(ReminderRow.remind_at.asc())
                .limit(max(1, limit))
                .all()
            )
            return [_reminder(row) for row in rows]


class AutomationStoreImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def list(self, owner_user_id: str) -> list[Automation]:
        self.ensure_defaults(owner_user_id)
        with session_scope(self._factory) as session:
            rows = (
                session.query(AutomationRow)
                .filter(AutomationRow.owner_user_id == owner_user_id)
                .order_by(AutomationRow.kind.asc())
                .all()
            )
            return [_automation(row) for row in rows]

    def get(self, automation_id: str) -> Automation | None:
        with session_scope(self._factory) as session:
            row = session.get(AutomationRow, automation_id)
            return _automation(row) if row else None

    def save(self, automation: Automation) -> None:
        with session_scope(self._factory) as session:
            row = session.get(AutomationRow, automation.id)
            if row is None:
                row = AutomationRow(id=automation.id, owner_user_id=automation.owner_user_id)
                session.add(row)
            row.kind = automation.kind
            row.enabled = 1 if automation.enabled else 0
            row.schedule_time = automation.schedule_time
            row.channels = list(automation.channels)
            row.last_run_at = automation.last_run_at
            row.last_result = automation.last_result
            row.last_run_id = automation.last_run_id
            if row.created_at is None:
                row.created_at = automation.created_at or _now()

    def ensure_defaults(self, owner_user_id: str) -> None:
        with session_scope(self._factory) as session:
            exists = (
                session.query(AutomationRow)
                .filter(
                    AutomationRow.owner_user_id == owner_user_id,
                    AutomationRow.kind == "daily_briefing",
                )
                .first()
            )
            if exists is not None:
                return
            session.add(
                AutomationRow(
                    id=uuid.uuid4().hex,
                    owner_user_id=owner_user_id,
                    kind="daily_briefing",
                    enabled=1,
                    schedule_time="08:00",
                    channels=["inbox", "telegram"],
                    created_at=_now(),
                )
            )


__all__ = ["AutomationStoreImpl", "ReminderStoreImpl"]
