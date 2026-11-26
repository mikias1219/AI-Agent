"""Habits: recurring check-ins with streaks (P1-2). Schedules come from the recurrence engine."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Protocol

from personal_agent.domain.recurrence import RecurrenceRule, due_on, iter_occurrences

CHECKIN_STATUSES = ("done", "skipped")
HABIT_KINDS = ("habit", "sleep", "weight", "water", "exercise", "prayer", "reading", "learning")
NAME_MAX = 120
NOTE_MAX = 300
LOOKBACK_DAYS = 366


@dataclass(slots=True)
class Habit:
    id: str
    owner_user_id: str
    name: str
    rule: RecurrenceRule
    kind: str = "habit"
    target_value: float | None = None  # e.g. 30 (minutes), 8 (glasses)
    target_unit: str = ""
    icon: str = ""
    archived: bool = False
    counts_toward_score: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class HabitCheckin:
    id: str
    habit_id: str
    owner_user_id: str
    day: date
    status: str = "done"
    value: float | None = None
    note: str = ""
    created_at: datetime | None = None


class HabitRepository(Protocol):
    def add(self, habit: Habit) -> None: ...
    def get(self, owner: str, habit_id: str) -> Habit | None: ...
    def save(self, habit: Habit) -> None: ...
    def list(self, owner: str, *, include_archived: bool = False) -> Sequence[Habit]: ...
    def upsert_checkin(self, checkin: HabitCheckin) -> HabitCheckin: ...
    def delete_checkin(self, owner: str, habit_id: str, day: date) -> bool: ...
    def checkins(
        self, owner: str, *, start: date, end: date, habit_id: str | None = None
    ) -> Sequence[HabitCheckin]: ...


def clean_name(value: Any) -> str:
    from personal_agent.domain.life import LifeError

    text = str(value or "").strip()
    if not text:
        raise LifeError("Habit name is required.")
    if len(text) > NAME_MAX:
        raise LifeError(f"Habit name must be at most {NAME_MAX} characters.")
    return text


def scheduled_days(habit: Habit, start: date, end: date) -> list[date]:
    return list(iter_occurrences(habit.rule, start, end))


def is_due(habit: Habit, day: date) -> bool:
    return not habit.archived and due_on(habit.rule, day)


@dataclass(frozen=True, slots=True)
class StreakResult:
    current: int
    best: int
    done_last_7: int
    due_last_7: int
    done_last_30: int
    due_last_30: int


def compute_streak(habit: Habit, checkins: Iterable[HabitCheckin], today: date) -> StreakResult:
    """Streak over *scheduled* days: a skipped day keeps the streak; a missed past day breaks it.

    Today does not break the streak while it is still open.
    """
    by_day = {c.day: c.status for c in checkins}
    start = max(habit.rule.start, today - timedelta(days=LOOKBACK_DAYS))
    days = scheduled_days(habit, start, today)
    current = best = run = 0
    for day in days:
        status = by_day.get(day)
        if status == "done":
            run += 1
            best = max(best, run)
        elif status == "skipped":
            continue
        elif day == today:
            continue  # still open
        else:
            run = 0
    current = run

    def window(span: int) -> tuple[int, int]:
        first = today - timedelta(days=span - 1)
        due = [d for d in days if d >= first and by_day.get(d) != "skipped"]
        done = [d for d in due if by_day.get(d) == "done"]
        return len(done), len(due)

    d7, due7 = window(7)
    d30, due30 = window(30)
    return StreakResult(current, best, d7, due7, d30, due30)


__all__ = [
    "CHECKIN_STATUSES",
    "HABIT_KINDS",
    "Habit",
    "HabitCheckin",
    "HabitRepository",
    "StreakResult",
    "clean_name",
    "compute_streak",
    "is_due",
    "scheduled_days",
]
