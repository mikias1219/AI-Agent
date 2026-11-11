"""Relative date resolution — pure, deterministic given `now` and a timezone.

`resolve_relative_date("friday 3pm", "Europe/Berlin", now=...)` turns the phrases people
type into a timezone-aware datetime. Calendar arithmetic is done on local wall-clock dates
(so DST shifts never move "tomorrow 9am" off 9:00), while "in N hours/minutes" is absolute.

Supported phrases (case-insensitive, optional leading "by"/"on"/"at"):
  today, tonight, tomorrow, <weekday>, next <weekday>, end of month,
  in N minutes|hours|days|weeks|months, YYYY-MM-DD,
  combined with a time: 3pm, 3:30pm, 15:00, noon, midnight.
A bare weekday means the next such day, today included; "next <weekday>" is strictly later.
Date without a time resolves to DEFAULT_HOUR:00. Time without a date is today if still
ahead of `now`, otherwise tomorrow. Unrecognised text returns None.
"""

from __future__ import annotations

import calendar
import re
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_HOUR = 9

_WEEKDAYS = {name.lower(): i for i, name in enumerate(calendar.day_name)}
_WEEKDAYS.update({name.lower(): i for i, name in enumerate(calendar.day_abbr)})
_WEEKDAYS["tues"] = 1
_WEEKDAYS["thur"] = 3
_WEEKDAYS["thurs"] = 3

_TIME_RE = re.compile(
    r"\b(?:(?P<h12>\d{1,2})(?::(?P<m12>\d{2}))?\s*(?P<ampm>am|pm)|(?P<h24>\d{1,2}):(?P<m24>\d{2})"
    r"|(?P<word>noon|midnight))\b"
)
_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_ISO_DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}")
_IN_RE = re.compile(r"\bin\s+(\d+)\s+(minute|hour|day|week|month)s?\b")
_PREFIX_RE = re.compile(r"^(?:by|on|at|due)\s+")


def get_zone(timezone: str) -> ZoneInfo:
    """Load an IANA timezone, raising ValueError for unknown names."""
    try:
        return ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"Unknown timezone: {timezone!r}") from exc


def add_months(day: date, months: int) -> date:
    """Add calendar months, clamping to the last day of the target month (Jan 31 + 1 → Feb 28)."""
    index = day.year * 12 + (day.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _localize(day: date, hour: int, minute: int, zone: ZoneInfo) -> datetime:
    """Wall-clock → aware datetime, normalising times that fall in a DST gap."""
    naive = datetime(day.year, day.month, day.day, hour, minute)
    return naive.replace(tzinfo=zone).astimezone(UTC).astimezone(zone)


def _parse_time(text: str) -> tuple[tuple[int, int] | None, str]:
    """Extract a time of day; returns ((hour, minute) | None, text without the time)."""
    match = _TIME_RE.search(text)
    if match is None:
        return None, text
    if match.group("word"):
        hour, minute = (12, 0) if match.group("word") == "noon" else (0, 0)
    elif match.group("ampm"):
        hour, minute = int(match.group("h12")), int(match.group("m12") or 0)
        if not 1 <= hour <= 12 or minute > 59:
            return None, text
        hour = hour % 12 + (12 if match.group("ampm") == "pm" else 0)
    else:
        hour, minute = int(match.group("h24")), int(match.group("m24"))
        if hour > 23 or minute > 59:
            return None, text
    rest = (text[: match.start()] + " " + text[match.end() :]).strip()
    return (hour, minute), re.sub(r"\s+", " ", rest)


def resolve_relative_date(
    text: str, timezone: str = "UTC", now: datetime | None = None
) -> datetime | None:
    """Resolve a phrase like 'tomorrow', 'friday 3pm' or 'in 2 weeks' to an aware datetime."""
    zone = get_zone(timezone)
    if now is None:
        now = datetime.now(UTC)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    local_now = now.astimezone(zone)
    today = local_now.date()

    cleaned = re.sub(r"\s+", " ", text.strip().lower().replace(",", " ")).strip()
    cleaned = _PREFIX_RE.sub("", cleaned)
    if not cleaned:
        return None

    relative = _IN_RE.fullmatch(cleaned)
    if relative:
        amount, unit = int(relative.group(1)), relative.group(2)
        if unit in ("minute", "hour"):
            delta = timedelta(minutes=amount) if unit == "minute" else timedelta(hours=amount)
            return (local_now.astimezone(UTC) + delta).astimezone(zone)
        shifted = (
            add_months(today, amount)
            if unit == "month"
            else today + timedelta(days=amount * (7 if unit == "week" else 1))
        )
        return _localize(shifted, local_now.hour, local_now.minute, zone)

    time_of_day, rest = _parse_time(cleaned)
    rest = re.sub(r"\s+(?:at|on|by)$", "", _PREFIX_RE.sub("", rest))

    target: date | None
    if rest == "":
        target = None
    elif rest in ("today", "tonight"):
        target = today
    elif rest == "tomorrow":
        target = today + timedelta(days=1)
    elif rest == "end of month":
        target = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    elif (iso := _ISO_RE.fullmatch(rest)) is not None:
        try:
            target = date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    else:
        strictly_later = rest.startswith("next ")
        name = rest.removeprefix("next ").strip()
        if name not in _WEEKDAYS:
            return None
        ahead = (_WEEKDAYS[name] - today.weekday()) % 7
        if strictly_later and ahead == 0:
            ahead = 7
        target = today + timedelta(days=ahead)

    if target is None:
        if time_of_day is None:
            return None
        candidate = _localize(today, *time_of_day, zone)
        if candidate <= local_now:
            candidate = _localize(today + timedelta(days=1), *time_of_day, zone)
        return candidate
    hour, minute = time_of_day if time_of_day is not None else (DEFAULT_HOUR, 0)
    if rest == "tonight" and time_of_day is None:
        hour, minute = 20, 0
    return _localize(target, hour, minute, zone)


def parse_due(text: str, timezone: str = "UTC", now: datetime | None = None) -> datetime:
    """Turn user/model text into an aware due datetime, or raise ValueError.

    Accepts an ISO 8601 datetime (naive values are read in `timezone`) or any phrase
    understood by `resolve_relative_date`.
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Due date must not be empty.")
    if _ISO_DATETIME_RE.match(cleaned):
        try:
            parsed = datetime.fromisoformat(cleaned)
        except ValueError:
            parsed = None
        if parsed is not None:
            return (
                parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=get_zone(timezone))
            )
    resolved = resolve_relative_date(cleaned, timezone, now=now)
    if resolved is None:
        raise ValueError(f"Could not understand due date {text!r}; use e.g. 'friday 3pm' or ISO.")
    return resolved
