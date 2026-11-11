"""Unit: relative date resolution, incl. DST and month-end edges."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from personal_agent.domain.dates import add_months, resolve_relative_date

BERLIN = ZoneInfo("Europe/Berlin")
NY = ZoneInfo("America/New_York")

# Wednesday 2026-11-11 10:00 in Berlin.
NOW = datetime(2026, 11, 11, 10, 0, tzinfo=BERLIN)


def local(dt: datetime | None, zone: ZoneInfo = BERLIN) -> tuple[int, int, int, int, int]:
    assert dt is not None
    d = dt.astimezone(zone)
    return d.year, d.month, d.day, d.hour, d.minute


def test_tomorrow_defaults_to_nine():
    assert local(resolve_relative_date("tomorrow", "Europe/Berlin", NOW)) == (2026, 11, 12, 9, 0)


def test_tomorrow_with_time_and_prefix():
    result = resolve_relative_date("by Tomorrow at 3pm", "Europe/Berlin", NOW)
    assert local(result) == (2026, 11, 12, 15, 0)
    assert result is not None and result.tzinfo is not None


def test_weekday_is_next_occurrence():
    assert local(resolve_relative_date("Friday", "Europe/Berlin", NOW)) == (2026, 11, 13, 9, 0)
    assert local(resolve_relative_date("friday 3:30pm", "Europe/Berlin", NOW)) == (
        2026,
        11,
        13,
        15,
        30,
    )


def test_same_weekday_today_vs_next():
    assert local(resolve_relative_date("wednesday", "Europe/Berlin", NOW)) == (2026, 11, 11, 9, 0)
    assert local(resolve_relative_date("next wednesday", "Europe/Berlin", NOW)) == (
        2026,
        11,
        18,
        9,
        0,
    )


def test_time_only_rolls_to_tomorrow_when_past():
    assert local(resolve_relative_date("3pm", "Europe/Berlin", NOW)) == (2026, 11, 11, 15, 0)
    assert local(resolve_relative_date("8am", "Europe/Berlin", NOW)) == (2026, 11, 12, 8, 0)
    assert local(resolve_relative_date("15:45", "Europe/Berlin", NOW)) == (2026, 11, 11, 15, 45)


def test_noon_midnight_and_12am_pm():
    assert local(resolve_relative_date("tomorrow noon", "Europe/Berlin", NOW)) == (
        2026,
        11,
        12,
        12,
        0,
    )
    assert local(resolve_relative_date("tomorrow 12am", "Europe/Berlin", NOW)) == (
        2026,
        11,
        12,
        0,
        0,
    )
    assert local(resolve_relative_date("tomorrow 12pm", "Europe/Berlin", NOW)) == (
        2026,
        11,
        12,
        12,
        0,
    )


def test_timezone_changes_the_local_day():
    # 23:30 UTC on the 11th is already the 12th in Berlin but still the 11th in New York.
    now = datetime(2026, 11, 11, 23, 30, tzinfo=UTC)
    assert local(resolve_relative_date("today 9am", "Europe/Berlin", now)) == (2026, 11, 12, 9, 0)
    assert local(resolve_relative_date("today 9am", "America/New_York", now), NY) == (
        2026,
        11,
        11,
        9,
        0,
    )


def test_unrecognised_and_invalid_input():
    assert resolve_relative_date("whenever", "UTC", NOW) is None
    assert resolve_relative_date("", "UTC", NOW) is None
    assert resolve_relative_date("tomorrow 25:00", "UTC", NOW) is None
    assert resolve_relative_date("13pm", "UTC", NOW) is None
    with pytest.raises(ValueError):
        resolve_relative_date("tomorrow", "Mars/Olympus", NOW)


def test_naive_now_is_treated_as_utc():
    result = resolve_relative_date("tomorrow 9am", "UTC", datetime(2026, 11, 11, 10, 0))
    assert result == datetime(2026, 11, 12, 9, 0, tzinfo=UTC)


# ---- DST -------------------------------------------------------------------------------


def test_tomorrow_keeps_wall_clock_across_spring_forward():
    # US DST starts 2026-03-08. 9am the day before is EST (-5); 9am after is EDT (-4).
    now = datetime(2026, 3, 7, 12, 0, tzinfo=NY)
    result = resolve_relative_date("tomorrow 9am", "America/New_York", now)
    assert local(result, NY) == (2026, 3, 8, 9, 0)
    assert result is not None and result.utcoffset().total_seconds() == -4 * 3600  # type: ignore[union-attr]


def test_tomorrow_keeps_wall_clock_across_fall_back():
    # Berlin DST ends 2026-10-25.
    now = datetime(2026, 10, 24, 12, 0, tzinfo=BERLIN)
    result = resolve_relative_date("tomorrow 9am", "Europe/Berlin", now)
    assert local(result) == (2026, 10, 25, 9, 0)
    assert result is not None and result.utcoffset().total_seconds() == 3600  # type: ignore[union-attr]


def test_nonexistent_spring_gap_time_is_normalised():
    # 02:30 on 2026-03-08 does not exist in New York; it must land on a real instant.
    now = datetime(2026, 3, 7, 12, 0, tzinfo=NY)
    result = resolve_relative_date("tomorrow 2:30am", "America/New_York", now)
    assert result is not None
    assert local(result, NY) == (2026, 3, 8, 3, 30)


def test_in_hours_is_absolute_across_dst():
    # 23:00 on Sat Oct 24 Berlin + 24h crosses fall-back: wall clock becomes 22:00 on the 25th.
    now = datetime(2026, 10, 24, 23, 0, tzinfo=BERLIN)
    result = resolve_relative_date("in 24 hours", "Europe/Berlin", now)
    assert result == now.astimezone(UTC).replace(day=25)
    assert local(result) == (2026, 10, 25, 22, 0)


def test_in_days_keeps_wall_clock_across_dst():
    now = datetime(2026, 10, 24, 23, 0, tzinfo=BERLIN)
    assert local(resolve_relative_date("in 1 day", "Europe/Berlin", now)) == (
        2026,
        10,
        25,
        23,
        0,
    )


# ---- month-end -------------------------------------------------------------------------


def test_add_months_clamps_to_month_end():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)  # leap year
    assert add_months(date(2026, 3, 31), 1) == date(2026, 4, 30)
    assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)  # year rollover
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)


def test_in_one_month_from_jan_31():
    now = datetime(2026, 1, 31, 10, 0, tzinfo=BERLIN)
    assert local(resolve_relative_date("in 1 month", "Europe/Berlin", now)) == (
        2026,
        2,
        28,
        10,
        0,
    )


def test_tomorrow_rolls_over_month_and_year_end():
    assert local(
        resolve_relative_date("tomorrow", "UTC", datetime(2026, 1, 31, 8, 0, tzinfo=UTC)), UTC
    ) == (2026, 2, 1, 9, 0)
    assert local(
        resolve_relative_date("tomorrow", "UTC", datetime(2026, 12, 31, 8, 0, tzinfo=UTC)), UTC
    ) == (2027, 1, 1, 9, 0)


def test_end_of_month_and_in_weeks():
    now = datetime(2026, 2, 10, 10, 0, tzinfo=UTC)
    assert local(resolve_relative_date("end of month", "UTC", now), UTC) == (2026, 2, 28, 9, 0)
    assert local(resolve_relative_date("in 3 weeks", "UTC", now), UTC) == (2026, 3, 3, 10, 0)


def test_iso_date():
    assert local(resolve_relative_date("2026-12-24 6pm", "UTC", NOW), UTC) == (2026, 12, 24, 18, 0)
    assert resolve_relative_date("2026-02-30", "UTC", NOW) is None
