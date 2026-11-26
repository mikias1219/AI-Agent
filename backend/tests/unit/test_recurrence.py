from datetime import date

import pytest

from personal_agent.domain.recurrence import RecurrenceError, due_on, occurrences, parse_rule


def rule(**kw):
    return parse_rule(kw)


def test_daily_interval_and_end():
    r = rule(freq="daily", interval=2, start="2026-11-01", end="2026-11-07")
    assert occurrences(r, date(2026, 11, 1), date(2026, 12, 31)) == [
        date(2026, 11, d) for d in (1, 3, 5, 7)
    ]
    assert occurrences(r, date(2026, 11, 2), date(2026, 11, 4)) == [date(2026, 11, 3)]


def test_weekly_weekdays():
    r = rule(freq="weekly", weekdays=[0, 4], start="2026-11-02")
    got = occurrences(r, date(2026, 11, 2), date(2026, 11, 15))
    assert got == [date(2026, 11, 2), date(2026, 11, 6), date(2026, 11, 9), date(2026, 11, 13)]


def test_monthly_day_31_falls_back_to_month_end():
    r = rule(freq="monthly", day_of_month=31, start="2026-01-31")
    got = occurrences(r, date(2026, 1, 1), date(2026, 4, 30))
    assert got == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]


def test_quarterly_and_yearly():
    q = rule(freq="quarterly", start="2026-01-15")
    assert occurrences(q, date(2026, 1, 1), date(2026, 12, 31)) == [
        date(2026, m, 15) for m in (1, 4, 7, 10)
    ]
    y = rule(freq="yearly", start="2024-02-29")
    assert occurrences(y, date(2024, 1, 1), date(2026, 12, 31)) == [
        date(2024, 2, 29),
        date(2025, 2, 28),
        date(2026, 2, 28),
    ]


def test_due_on_and_validation():
    r = rule(freq="weekly", start="2026-11-02")
    assert due_on(r, date(2026, 11, 9)) and not due_on(r, date(2026, 11, 10))
    for bad in (
        {"freq": "hourly", "start": "2026-01-01"},
        {"freq": "daily", "start": "2026-01-01", "recurrence": 1},
        {"freq": "daily", "start": "2026-02-01", "end": "2026-01-01"},
        {"freq": "daily", "start": "2026-01-01", "weekdays": [1]},
        {"freq": "daily", "interval": 0, "start": "2026-01-01"},
    ):
        with pytest.raises(RecurrenceError):
            parse_rule(bad)
