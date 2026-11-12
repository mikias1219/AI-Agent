"""Quiet hours and daily proactive cap checks (BR proactive output)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True, slots=True)
class ProactiveDecision:
    allowed: bool
    reason: str = ""


def _parse_hhmm(value: str | None) -> time | None:
    if not value or not value.strip():
        return None
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return time(hour, minute)


def in_quiet_hours(local_now: datetime, start: str | None, end: str | None) -> bool:
    """Return True when local_now falls inside [start, end) in owner-local time.

    Crossing midnight is supported (e.g. 22:00–07:00). Empty start or end disables quiet hours.
    """
    start_t = _parse_hhmm(start)
    end_t = _parse_hhmm(end)
    if start_t is None or end_t is None:
        return False
    current = time(local_now.hour, local_now.minute, local_now.second)
    if start_t <= end_t:
        return start_t <= current < end_t
    # Overnight window: quiet if >= start OR < end
    return current >= start_t or current < end_t


def decide_proactive_send(
    *,
    local_now: datetime,
    paused: bool,
    quiet_hours_start: str | None,
    quiet_hours_end: str | None,
    proactive_used: int,
    proactive_cap: int,
) -> ProactiveDecision:
    if paused:
        return ProactiveDecision(False, "paused")
    if in_quiet_hours(local_now, quiet_hours_start, quiet_hours_end):
        return ProactiveDecision(False, "quiet_hours")
    if proactive_used >= proactive_cap:
        return ProactiveDecision(False, "daily_cap")
    return ProactiveDecision(True, "")
