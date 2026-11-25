"""Outcome rules, score, streak and plan-date maths (contract section 7). Pure, no I/O."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from personal_agent.domain.days import (
    DaySummary,
    counts_for_streak,
    effective_outcome,
    period_stats,
    score_of,
    streak_days,
    summarize,
)
from personal_agent.domain.models import Task, TaskStatus
from personal_agent.domain.task_rules import (
    IllegalTaskTransitionError,
    complete,
    default_plan_date,
    has_time_of_day,
    infer_outcome,
    local_date,
    new_task,
    reopen,
    transition,
)

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def task(**kwargs: object) -> Task:
    base = new_task("o", "Push-ups", now=NOW)
    for key, value in kwargs.items():
        setattr(base, key, value)
    return base


# -- outcome inference and completion ----------------------------------------------------------


@pytest.mark.parametrize(
    ("target", "actual", "expected"),
    [
        (30, 30, "achieved"),
        (30, 45, "achieved"),
        (30, 12, "partial"),
        (30, 0, "missed"),
        (None, 5, "achieved"),
        (30, None, "achieved"),
        (None, None, "achieved"),
    ],
)
def test_infer_outcome(target, actual, expected) -> None:
    assert infer_outcome(target, actual) == expected


def test_complete_achieved_and_partial_close_the_task() -> None:
    for outcome in ("achieved", "partial"):
        t = complete(task(), outcome=outcome, now=NOW)
        assert t.status is TaskStatus.DONE and t.completed_at == NOW and t.outcome == outcome


@pytest.mark.parametrize("outcome", ["missed", "skipped"])
def test_complete_missed_or_skipped_cancels_without_completion_time(outcome) -> None:
    t = complete(task(completed_at=NOW), outcome=outcome, now=NOW)
    assert t.status is TaskStatus.CANCELLED and t.completed_at is None and t.outcome == outcome


def test_complete_infers_from_target_and_actual() -> None:
    t = complete(task(target_value=30.0), actual_value=12, now=NOW)
    assert (t.outcome, t.status, t.actual_value) == ("partial", TaskStatus.DONE, 12.0)
    zero = complete(task(target_value=30.0), actual_value=0, now=NOW)
    assert (zero.outcome, zero.status) == ("missed", TaskStatus.CANCELLED)


def test_owner_may_override_the_inferred_outcome() -> None:
    t = complete(task(target_value=30.0), outcome="achieved", actual_value=5, now=NOW)
    assert t.outcome == "achieved" and t.actual_value == 5.0


def test_complete_validates_input() -> None:
    with pytest.raises(ValueError, match="0 or more"):
        complete(task(), actual_value=-1, now=NOW)
    with pytest.raises(ValueError, match="outcome must be one of"):
        complete(task(), outcome="great", now=NOW)
    with pytest.raises(ValueError, match="at most 500"):
        complete(task(), note="x" * 501, now=NOW)


def test_complete_stores_note_and_works_as_a_correction() -> None:
    t = complete(task(), outcome="achieved", note="felt good", now=NOW)
    assert t.outcome_note == "felt good"
    fixed = complete(t, outcome="missed", now=NOW + timedelta(minutes=1))
    assert fixed.status is TaskStatus.CANCELLED and fixed.completed_at is None


def test_reopen_clears_outcome_actual_and_completion() -> None:
    for outcome in ("achieved", "missed"):
        t = complete(task(target_value=30.0), outcome=outcome, actual_value=10, now=NOW)
        reopen(t, now=NOW)
        assert t.status is TaskStatus.PLANNED
        assert (t.outcome, t.actual_value, t.completed_at) == (None, None, None)
        assert t.target_value == 30.0  # the plan itself stays


def test_reopen_refuses_open_tasks() -> None:
    with pytest.raises(IllegalTaskTransitionError):
        reopen(task())


def test_plain_status_changes_keep_outcomes_consistent() -> None:
    done = transition(task(), TaskStatus.DONE, now=NOW)
    assert done.outcome == "achieved"
    skipped = transition(task(), TaskStatus.CANCELLED, now=NOW)
    assert skipped.outcome == "skipped"
    transition(done, TaskStatus.PLANNED, now=NOW)
    assert done.outcome is None


# -- plan date and timezone --------------------------------------------------------------------


def test_default_plan_date_is_due_date_in_owner_timezone() -> None:
    due = datetime(2026, 11, 25, 23, 30, tzinfo=UTC)  # already the 26th in Nairobi
    assert default_plan_date(due, NOW, "Africa/Nairobi") == date(2026, 11, 26)
    assert default_plan_date(due, NOW, "America/New_York") == date(2026, 11, 25)
    assert default_plan_date(None, NOW, "UTC") == date(2026, 11, 25)


def test_new_task_plan_date_defaults_and_explicit() -> None:
    assert new_task("o", "x", now=NOW).plan_date == date(2026, 11, 25)
    assert new_task("o", "x", plan_date=date(2027, 1, 2), now=NOW).plan_date == date(2027, 1, 2)
    late = new_task("o", "x", now=datetime(2026, 11, 25, 23, 30, tzinfo=UTC), timezone="Asia/Tokyo")
    assert late.plan_date == date(2026, 11, 26)


def test_plan_date_across_dst_edges() -> None:
    # US spring forward 2026-03-08 and fall back 2026-11-01 (New York).
    spring = datetime(2026, 3, 9, 3, 30, tzinfo=UTC)  # 23:30 EDT on the 8th
    assert local_date(spring, "America/New_York") == date(2026, 3, 8)
    fall = datetime(2026, 11, 1, 4, 30, tzinfo=UTC)  # 00:30 EDT on the 1st
    assert local_date(fall, "America/New_York") == date(2026, 11, 1)
    after = datetime(2026, 11, 1, 5, 30, tzinfo=UTC)  # 01:30 EDT, before the repeated hour
    assert local_date(after, "America/New_York") == date(2026, 11, 1)
    repeated = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)  # 01:30 EST (second pass)
    assert local_date(repeated, "America/New_York") == date(2026, 11, 1)
    nonexistent = datetime(2026, 3, 8, 7, 30, tzinfo=UTC)  # 03:30 EDT (02:30 does not exist)
    assert local_date(nonexistent, "America/New_York") == date(2026, 3, 8)


def test_has_time_of_day_treats_date_only_defaults_as_untimed() -> None:
    assert has_time_of_day(datetime(2026, 11, 25, 15, 30, tzinfo=UTC), "UTC")
    assert not has_time_of_day(datetime(2026, 11, 25, 9, 0, tzinfo=UTC), "UTC")
    assert not has_time_of_day(datetime(2026, 11, 25, 0, 0, tzinfo=UTC), "UTC")
    assert has_time_of_day(datetime(2026, 11, 25, 6, 0, tzinfo=UTC), "Africa/Nairobi") is False
    assert not has_time_of_day(None, "UTC")


# -- summary and score -------------------------------------------------------------------------


def closed(outcome: str) -> Task:
    return complete(task(), outcome=outcome, now=NOW)


def test_summary_counts_and_score() -> None:
    tasks = [
        closed("achieved"),
        closed("achieved"),
        closed("partial"),
        closed("missed"),
        closed("skipped"),
        task(),
        task(status=TaskStatus.BLOCKED),
    ]
    s = summarize(tasks)
    assert (s.planned, s.done, s.achieved, s.partial) == (7, 3, 2, 1)
    assert (s.missed, s.skipped, s.open) == (1, 1, 2)
    assert s.score == round((2 + 0.5) / 6, 4)
    assert s.to_dict()["score"] == s.score


def test_score_is_none_when_nothing_counts() -> None:
    assert summarize([]).score is None
    assert summarize([closed("skipped"), closed("skipped")]).score is None
    assert score_of(0, 0, 0) is None


def test_legacy_closed_tasks_count_by_status() -> None:
    legacy_done = task(status=TaskStatus.DONE)
    legacy_cancelled = task(status=TaskStatus.CANCELLED)
    assert effective_outcome(legacy_done) == "achieved"
    assert effective_outcome(legacy_cancelled) == "skipped"
    s = summarize([legacy_done, legacy_cancelled])
    assert (s.achieved, s.skipped, s.score) == (1, 1, 1.0)


# -- streak ------------------------------------------------------------------------------------


def day(achieved=0, partial=0, missed=0, skipped=0, open_=0) -> DaySummary:
    planned = achieved + partial + missed + skipped + open_
    return DaySummary(planned, achieved + partial, achieved, partial, missed, skipped, open_)


TODAY = date(2026, 11, 25)


def run(days: dict[int, DaySummary]) -> int:
    return streak_days({TODAY - timedelta(days=ago): s for ago, s in days.items()}, TODAY)


def test_threshold_is_exactly_point_eight() -> None:
    assert counts_for_streak(day(achieved=4, missed=1))  # 0.8 exactly
    assert not counts_for_streak(day(achieved=3, missed=2))
    assert counts_for_streak(day(achieved=3, partial=2))  # (3 + 1) / 5 = 0.8
    assert not counts_for_streak(day(achieved=3, partial=1, missed=1))  # 3.5 / 5 = 0.7
    assert counts_for_streak(day(achieved=1, skipped=2))  # skipped leaves the denominator
    assert not counts_for_streak(day(skipped=2))  # nothing counts
    assert not counts_for_streak(DaySummary())  # no tasks
    assert not counts_for_streak(day(achieved=4, open_=1))  # still open


def test_streak_counts_consecutive_days_including_today() -> None:
    assert run({0: day(achieved=2), 1: day(achieved=1), 2: day(achieved=3)}) == 3


def test_streak_ends_yesterday_while_today_is_unfinished_or_empty() -> None:
    assert run({0: day(achieved=1, open_=1), 1: day(achieved=2), 2: day(achieved=2)}) == 2
    assert run({1: day(achieved=2), 2: day(achieved=2)}) == 2  # no tasks today yet


def test_finished_but_failing_today_resets_the_streak() -> None:
    assert run({0: day(achieved=1, missed=2), 1: day(achieved=2)}) == 0


def test_gap_or_failing_day_breaks_the_streak() -> None:
    assert run({0: day(achieved=1), 2: day(achieved=1)}) == 1  # day -1 has no tasks
    failing_yesterday = {0: day(achieved=1), 1: day(achieved=1, missed=1), 2: day(achieved=3)}
    assert run(failing_yesterday) == 1


def test_streak_with_no_data_and_old_data() -> None:
    assert streak_days({}, TODAY) == 0
    assert run({5: day(achieved=3)}) == 0


def test_period_stats_aggregates_counts_and_rate() -> None:
    stats = period_stats([day(achieved=2, missed=1), day(achieved=1, partial=2, skipped=1)])
    assert stats == {
        "planned": 7,
        "achieved": 3,
        "partial": 2,
        "missed": 1,
        "rate": round(4 / 6, 4),
    }
    assert period_stats([])["rate"] is None
