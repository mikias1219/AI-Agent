"""Recurrence engine shared by habits, finance bills/income and recurring tasks (P1-1).

A rule is a small, validated value object (daily / weekly / monthly / quarterly / yearly,
interval, optional weekdays or day-of-month, start and optional end date). Occurrences are
pure functions of the rule, so generating them is idempotent: callers store them under a
unique (rule, date) key. Month-end rule: a due day of 31 falls back to the last day of
shorter months.
"""

from __future__ import annotations

import calendar
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

FREQUENCIES = ("daily", "weekly", "monthly", "quarterly", "yearly")
MAX_INTERVAL = 365
MAX_OCCURRENCES = 1000


class RecurrenceError(ValueError):
    """The recurrence rule is invalid."""


@dataclass(frozen=True, slots=True)
class RecurrenceRule:
    freq: str
    start: date
    interval: int = 1
    weekdays: tuple[int, ...] = field(default_factory=tuple)  # 0=Mon .. 6=Sun (weekly)
    day_of_month: int | None = None  # monthly / quarterly / yearly; 1..31
    end: date | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "freq": self.freq,
            "interval": self.interval,
            "weekdays": list(self.weekdays),
            "day_of_month": self.day_of_month,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
        }


def _day(value: Any, name: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise RecurrenceError(f"{name} must be a YYYY-MM-DD date.") from exc


def parse_rule(data: Mapping[str, Any], *, default_start: date | None = None) -> RecurrenceRule:
    """Validate a rule mapping; unknown keys are rejected rather than dropped."""
    allowed = {"freq", "interval", "weekdays", "day_of_month", "start", "end"}
    unknown = set(data) - allowed
    if unknown:
        raise RecurrenceError(f"Unknown recurrence field(s): {', '.join(sorted(unknown))}.")
    freq = str(data.get("freq") or "").lower()
    if freq not in FREQUENCIES:
        raise RecurrenceError(f"freq must be one of: {', '.join(FREQUENCIES)}.")
    interval = data.get("interval", 1)
    if (
        isinstance(interval, bool)
        or not isinstance(interval, int)
        or not 1 <= interval <= MAX_INTERVAL
    ):
        raise RecurrenceError(f"interval must be a whole number from 1 to {MAX_INTERVAL}.")
    start_raw = data.get("start") or default_start
    if start_raw is None:
        raise RecurrenceError("start date is required.")
    start = _day(start_raw, "start")
    end = _day(data["end"], "end") if data.get("end") else None
    if end is not None and end < start:
        raise RecurrenceError("end must not be before start.")
    weekdays_raw = data.get("weekdays") or []
    if not isinstance(weekdays_raw, (list, tuple)):
        raise RecurrenceError("weekdays must be a list of 0 (Mon) to 6 (Sun).")
    weekdays = tuple(sorted({int(w) for w in weekdays_raw}))
    if any(w < 0 or w > 6 for w in weekdays):
        raise RecurrenceError("weekdays must be between 0 (Mon) and 6 (Sun).")
    if weekdays and freq != "weekly":
        raise RecurrenceError("weekdays only apply to weekly rules.")
    dom = data.get("day_of_month")
    if dom is not None:
        if freq not in ("monthly", "quarterly", "yearly"):
            raise RecurrenceError("day_of_month only applies to monthly, quarterly or yearly.")
        if isinstance(dom, bool) or not isinstance(dom, int) or not 1 <= dom <= 31:
            raise RecurrenceError("day_of_month must be 1 to 31.")
    return RecurrenceRule(freq, start, interval, weekdays, dom, end)


def _clamped(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _add_months(year: int, month: int, months: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + months
    return index // 12, index % 12 + 1


def iter_occurrences(rule: RecurrenceRule, from_day: date, to_day: date) -> Iterator[date]:
    """Yield each occurrence date within [from_day, to_day], oldest first."""
    last = min(to_day, rule.end) if rule.end else to_day
    first = max(from_day, rule.start)
    if first > last:
        return
    emitted = 0
    if rule.freq == "daily":
        gap = (first - rule.start).days
        current = rule.start + timedelta(days=gap + (-gap) % rule.interval)
        while current <= last and emitted < MAX_OCCURRENCES:
            yield current
            emitted += 1
            current += timedelta(days=rule.interval)
        return
    if rule.freq == "weekly":
        days = rule.weekdays or (rule.start.weekday(),)
        week0 = rule.start - timedelta(days=rule.start.weekday())
        current = first - timedelta(days=first.weekday())
        while current <= last and emitted < MAX_OCCURRENCES:
            if ((current - week0).days // 7) % rule.interval == 0:
                for wd in days:
                    candidate = current + timedelta(days=wd)
                    if first <= candidate <= last:
                        yield candidate
                        emitted += 1
            current += timedelta(days=7)
        return
    step = {"monthly": 1, "quarterly": 3, "yearly": 12}[rule.freq] * rule.interval
    dom = rule.day_of_month or rule.start.day
    year, month = rule.start.year, rule.start.month
    while True:
        candidate = _clamped(year, month, dom)
        if candidate > last or emitted >= MAX_OCCURRENCES:
            return
        if candidate >= first and candidate >= rule.start:
            yield candidate
            emitted += 1
        year, month = _add_months(year, month, step)


def occurrences(rule: RecurrenceRule, from_day: date, to_day: date) -> list[date]:
    return list(iter_occurrences(rule, from_day, to_day))


def due_on(rule: RecurrenceRule, day: date) -> bool:
    return any(True for _ in iter_occurrences(rule, day, day))
