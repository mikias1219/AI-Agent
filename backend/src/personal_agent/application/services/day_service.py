"""Days: what was planned, what was achieved, score and streak (contract section 7).

The owner timezone decides which day "today" is and which day a task belongs to. Dates are
plain `date` values from there on, so DST changes never move a task to another day.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from personal_agent.application.life_payloads import note_payload, reading_log_payload
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.task_service import TaskService
from personal_agent.application.task_payloads import task_payload
from personal_agent.domain.dates import get_zone
from personal_agent.domain.days import (
    MAX_RANGE_DAYS,
    DaySummary,
    month_start,
    period_stats,
    streak_days,
    summarize,
    week_start,
)
from personal_agent.domain.life import LifeError
from personal_agent.domain.models import Task
from personal_agent.domain.ports import AuditLog, LearnRepository, NoteRepository, ReadingRepository
from personal_agent.domain.task_rules import OPEN_STATUSES, local_date

logger = logging.getLogger(__name__)

EventsFetcher = Callable[[str, str], list[dict[str, Any]]]
_ALL = 100_000


def parse_day(value: str | None, name: str = "date") -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise LifeError(f"{name} must be a date like 2026-11-25.") from None


class DayService:
    def __init__(
        self,
        *,
        tasks: TaskService,
        profiles: ProfileService,
        notes: NoteRepository,
        reading: ReadingRepository,
        learn: LearnRepository,
        events: EventsFetcher | None = None,
        calendar_connected: Callable[[], bool] | None = None,
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._tasks = tasks
        self._profiles = profiles
        self._notes = notes
        self._reading = reading
        self._learn = learn
        self._events = events
        self._connected = calendar_connected or (lambda: False)
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    # -- basics ----------------------------------------------------------------------

    def timezone(self, owner: str) -> str:
        return self._profiles.timezone_for(owner)

    def today(self, owner: str) -> date:
        return local_date(self._clock(), self.timezone(owner))

    def tasks_of(self, owner: str, day: date) -> list[Task]:
        return self._tasks.tasks_on(owner, day)

    def tasks_until(self, owner: str, last: date) -> list[Task]:
        return self._tasks.tasks_between(owner, date.min, last)

    def summary_of(self, owner: str, day: date) -> DaySummary:
        return summarize(self.tasks_of(owner, day))

    def readings_of(self, owner: str, day: date) -> list[Any]:
        return [
            log
            for log in self._reading.list_logs(owner, plan_id="", limit=_ALL, offset=0)
            if log.read_on == day
        ]

    def reviewed_on(self, owner: str, day: date) -> int:
        zone = get_zone(self.timezone(owner))
        return sum(
            1 for moment in self._learn.review_times(owner) if moment.astimezone(zone).date() == day
        )

    # -- the day ---------------------------------------------------------------------

    def day(self, owner: str, day: date) -> dict[str, Any]:
        tasks = self.tasks_of(owner, day)
        diary = self._notes.find_diary(owner, day)
        connected = self._connected()
        return {
            "date": day.isoformat(),
            "is_today": day == self.today(owner),
            "tasks": [task_payload(t) for t in tasks],
            "summary": summarize(tasks).to_dict(),
            "events": self._events_on(owner, day) if connected else [],
            "calendar_connected": connected,
            "diary": note_payload(diary) if diary else None,
            "readings": [reading_log_payload(r) for r in self.readings_of(owner, day)],
            "learned": {"reviewed": self.reviewed_on(owner, day)},
        }

    def _events_on(self, owner: str, day: date) -> list[dict[str, Any]]:
        if self._events is None:
            return []
        zone = get_zone(self.timezone(owner))
        start = datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
        try:
            return list(
                self._events(
                    start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")
                )
            )
        except Exception as exc:  # noqa: BLE001 - the day still renders without calendar events
            logger.warning("Calendar events unavailable for %s: %s", day, exc)
            return []

    def range(self, owner: str, start: date, end: date) -> list[dict[str, Any]]:
        if end < start:
            raise LifeError("from must not be after to.")
        if (end - start).days + 1 > MAX_RANGE_DAYS:
            raise LifeError(f"The range may cover at most {MAX_RANGE_DAYS} days.")
        grouped: dict[date, list[Task]] = defaultdict(list)
        for task in self._tasks.tasks_between(owner, start, end):
            assert task.plan_date is not None
            grouped[task.plan_date].append(task)
        rows = []
        for day in sorted(grouped):
            s = summarize(grouped[day])
            rows.append(
                {
                    "date": day.isoformat(),
                    "planned": s.planned,
                    "achieved": s.achieved,
                    "partial": s.partial,
                    "missed": s.missed,
                    "skipped": s.skipped,
                    "open": s.open,
                    "score": s.score,
                }
            )
        return rows

    def stats(self, owner: str) -> dict[str, Any]:
        grouped: dict[date, list[Task]] = defaultdict(list)
        for task in self._tasks.tasks_between(owner, date.min, date.max):
            assert task.plan_date is not None
            grouped[task.plan_date].append(task)
        by_date = {day: summarize(items) for day, items in grouped.items()}
        today = self.today(owner)
        week = [s for d, s in by_date.items() if week_start(today) <= d <= today]
        month = [s for d, s in by_date.items() if month_start(today) <= d <= today]
        return {
            "streak_days": streak_days(by_date, today),
            "week": period_stats(week),
            "month": period_stats(month),
        }

    def carry_over(self, owner: str, day: date, to: date | None = None) -> dict[str, Any]:
        target = to or day + timedelta(days=1)
        moved = self._tasks.carry_over(owner, day, target)
        return {"moved": len(moved), "to": target.isoformat(), "task_ids": [t.id for t in moved]}

    # -- Today -----------------------------------------------------------------------

    def today_block(self, owner: str) -> dict[str, Any]:
        day = self.today(owner)
        tasks = self.tasks_of(owner, day)
        open_tasks = [t for t in tasks if t.status in OPEN_STATUSES]
        open_tasks.sort(
            key=lambda t: (t.due_at is None, t.due_at or datetime.max.replace(tzinfo=UTC), t.id)
        )
        nxt = open_tasks[0] if open_tasks else None
        return {
            "date": day.isoformat(),
            "summary": summarize(tasks).to_dict(),
            "next_task": (
                {
                    "id": nxt.id,
                    "title": nxt.title,
                    "due_at": nxt.due_at.isoformat() if nxt.due_at else None,
                }
                if nxt
                else None
            ),
        }

    def open_ids(self, owner: str, day: date) -> list[str]:
        return [t.id for t in self.tasks_of(owner, day) if t.status in OPEN_STATUSES]


__all__ = ["DayService", "parse_day"]
