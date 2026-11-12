"""Quiet hours and daily proactive cap (Task 8)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from personal_agent.application.services.proactive_gate import (
    decide_proactive_send,
    in_quiet_hours,
)


def test_in_quiet_hours_same_day() -> None:
    local = datetime(2026, 11, 12, 23, 0, tzinfo=ZoneInfo("UTC"))
    assert in_quiet_hours(local, "22:00", "23:30")
    assert not in_quiet_hours(local, "08:00", "09:00")


def test_in_quiet_hours_overnight() -> None:
    late = datetime(2026, 11, 12, 23, 30, tzinfo=ZoneInfo("UTC"))
    early = datetime(2026, 11, 13, 6, 0, tzinfo=ZoneInfo("UTC"))
    midday = datetime(2026, 11, 13, 12, 0, tzinfo=ZoneInfo("UTC"))
    assert in_quiet_hours(late, "22:00", "07:00")
    assert in_quiet_hours(early, "22:00", "07:00")
    assert not in_quiet_hours(midday, "22:00", "07:00")


def test_empty_quiet_hours_disabled() -> None:
    local = datetime(2026, 11, 12, 23, 0, tzinfo=ZoneInfo("UTC"))
    assert not in_quiet_hours(local, "", "07:00")
    assert not in_quiet_hours(local, "22:00", "")


def test_decide_blocks_paused() -> None:
    local = datetime(2026, 11, 12, 10, 0, tzinfo=ZoneInfo("UTC"))
    decision = decide_proactive_send(
        local_now=local,
        paused=True,
        quiet_hours_start=None,
        quiet_hours_end=None,
        proactive_used=0,
        proactive_cap=3,
    )
    assert not decision.allowed
    assert decision.reason == "paused"


def test_decide_blocks_quiet_hours() -> None:
    local = datetime(2026, 11, 12, 23, 0, tzinfo=ZoneInfo("UTC"))
    decision = decide_proactive_send(
        local_now=local,
        paused=False,
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
        proactive_used=0,
        proactive_cap=3,
    )
    assert not decision.allowed
    assert decision.reason == "quiet_hours"


def test_decide_blocks_daily_cap() -> None:
    local = datetime(2026, 11, 12, 10, 0, tzinfo=ZoneInfo("UTC"))
    decision = decide_proactive_send(
        local_now=local,
        paused=False,
        quiet_hours_start=None,
        quiet_hours_end=None,
        proactive_used=3,
        proactive_cap=3,
    )
    assert not decision.allowed
    assert decision.reason == "daily_cap"


def test_decide_allows_when_clear() -> None:
    local = datetime(2026, 11, 12, 10, 0, tzinfo=ZoneInfo("UTC"))
    decision = decide_proactive_send(
        local_now=local,
        paused=False,
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
        proactive_used=1,
        proactive_cap=3,
    )
    assert decision.allowed
