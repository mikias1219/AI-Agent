"""Time tracking service: one running timer, manual entries, totals by task/project/day."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable, Mapping
from datetime import date, datetime, time, timedelta
from typing import Any

from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.domain.dates import get_zone
from personal_agent.domain.life import LifeError
from personal_agent.domain.timetrack import (
    MAX_MANUAL_MINUTES,
    NOTE_MAX,
    TimeEntry,
    TimeRepository,
)

MAX_RANGE_DAYS = 120


def entry_payload(entry: TimeEntry, now: datetime) -> dict[str, Any]:
    return {
        "id": entry.id,
        "task_id": entry.task_id,
        "goal_id": entry.goal_id,
        "project": entry.project,
        "note": entry.note,
        "started_at": entry.started_at.isoformat(),
        "ended_at": entry.ended_at.isoformat() if entry.ended_at else None,
        "minutes": entry.minutes(now),
        "running": entry.ended_at is None,
        "source": entry.source,
    }


class TimeService:
    def __init__(
        self,
        repository: TimeRepository,
        ctx: LifeContext,
        *,
        task_project: Callable[[str], str | None],
    ) -> None:
        self._repo = repository
        self._ctx = ctx
        self._task_project = task_project  # task id -> its project, None if the task is unknown

    def _note(self, value: Any) -> str:
        text = str(value or "").strip()
        if len(text) > NOTE_MAX:
            raise LifeError(f"note must be at most {NOTE_MAX} characters.")
        return text

    def _links(
        self, task_id: str | None, project: str, goal_id: str | None
    ) -> tuple[str | None, str, str | None]:
        if task_id:
            found = self._task_project(task_id)
            if found is None:
                raise not_found("Task")
            project = project or found  # the task's own project unless one is given
        return task_id or None, project.strip()[:128], goal_id or None

    def start(
        self,
        owner: str,
        *,
        task_id: str | None = None,
        project: str = "",
        goal_id: str | None = None,
        note: str = "",
    ) -> TimeEntry:
        """Start the timer; a timer already running is stopped first (only one at a time)."""
        now = self._ctx.now()
        current = self._repo.running(owner)
        if current is not None:
            current.ended_at = now
            self._repo.save(current)
        task, proj, goal = self._links(task_id, project, goal_id)
        entry = TimeEntry(
            uuid.uuid4().hex, owner, now, None, task, goal, proj, self._note(note), "timer"
        )
        self._repo.add(entry)
        self._ctx.record("time.started", owner, entry_id=entry.id)
        return entry

    def stop(self, owner: str) -> TimeEntry:
        entry = self._repo.running(owner)
        if entry is None:
            raise LifeError("No timer is running.")
        entry.ended_at = self._ctx.now()
        self._repo.save(entry)
        self._ctx.record("time.stopped", owner, entry_id=entry.id)
        return entry

    def running(self, owner: str) -> TimeEntry | None:
        return self._repo.running(owner)

    def add_manual(self, owner: str, data: Mapping[str, Any]) -> TimeEntry:
        allowed = {"minutes", "day", "task_id", "project", "goal_id", "note"}
        unknown = set(data) - allowed
        if unknown:
            raise LifeError(f"Unknown field(s): {', '.join(sorted(unknown))}.")
        minutes = data.get("minutes")
        if (
            isinstance(minutes, bool)
            or not isinstance(minutes, int)
            or not 1 <= minutes <= MAX_MANUAL_MINUTES
        ):
            raise LifeError(f"minutes must be a whole number from 1 to {MAX_MANUAL_MINUTES}.")
        today = self._ctx.today(owner)
        try:
            day = date.fromisoformat(str(data["day"])) if data.get("day") else today
        except ValueError as exc:
            raise LifeError("day must be YYYY-MM-DD.") from exc
        if day > today:
            raise LifeError("You can't log time in the future.")
        zone = get_zone(self._ctx._profiles.timezone_for(owner))  # noqa: SLF001
        start = datetime.combine(day, time(9, 0), tzinfo=zone)
        task, proj, goal = self._links(
            data.get("task_id"), str(data.get("project") or ""), data.get("goal_id")
        )
        entry = TimeEntry(
            uuid.uuid4().hex, owner, start, start + timedelta(minutes=minutes), task, goal, proj,
            self._note(data.get("note")), "manual",
        )  # fmt: skip
        self._repo.add(entry)
        self._ctx.record("time.logged", owner, entry_id=entry.id, minutes=minutes)
        return entry

    def delete(self, owner: str, entry_id: str) -> None:
        if not self._repo.delete(owner, entry_id):
            raise not_found("Time entry")

    def _range(self, owner: str, start: date, end: date) -> list[TimeEntry]:
        if end < start or (end - start).days > MAX_RANGE_DAYS:
            raise LifeError(f"from/to must be a valid range of at most {MAX_RANGE_DAYS} days.")
        zone = get_zone(self._ctx._profiles.timezone_for(owner))  # noqa: SLF001
        lo = datetime.combine(start, time.min, tzinfo=zone)
        hi = datetime.combine(end + timedelta(days=1), time.min, tzinfo=zone)
        return list(self._repo.between(owner, lo, hi))

    def entries(self, owner: str, start: date, end: date) -> list[dict[str, Any]]:
        now = self._ctx.now()
        return [entry_payload(e, now) for e in self._range(owner, start, end)]

    def summary(self, owner: str, start: date, end: date) -> dict[str, Any]:
        """Where did my time go: minutes by day, project and task."""
        now = self._ctx.now()
        zone = get_zone(self._ctx._profiles.timezone_for(owner))  # noqa: SLF001
        by_day: dict[str, int] = defaultdict(int)
        by_project: dict[str, int] = defaultdict(int)
        by_task: dict[str, int] = defaultdict(int)
        total = 0
        for entry in self._range(owner, start, end):
            minutes = entry.minutes(now)
            total += minutes
            by_day[entry.started_at.astimezone(zone).date().isoformat()] += minutes
            by_project[entry.project or "No project"] += minutes
            if entry.task_id:
                by_task[entry.task_id] += minutes
        return {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "total_minutes": total,
            "by_day": dict(sorted(by_day.items())),
            "by_project": sorted(
                ({"project": k, "minutes": v} for k, v in by_project.items()),
                key=lambda r: -r["minutes"],
            ),
            "by_task": sorted(
                ({"task_id": k, "minutes": v} for k, v in by_task.items()),
                key=lambda r: -r["minutes"],
            ),
        }

    def minutes_for_goal(self, owner: str, goal_id: str) -> int:
        now = self._ctx.now()
        epoch = self._ctx.today(owner) - timedelta(days=MAX_RANGE_DAYS)
        return sum(
            e.minutes(now)
            for e in self._range(owner, epoch, self._ctx.today(owner))
            if e.goal_id == goal_id
        )
