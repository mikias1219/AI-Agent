"""Day summaries, scores and streaks — pure maths (contract section 7).

`score` = (achieved + 0.5 * partial) / (planned - skipped), or None when nothing counts.
A day counts toward the streak when it has at least one task, no open tasks and score >= 0.8.
Everything here works on plain dates, so DST shifts never move a task to another day; the
owner-timezone conversion happens once, in `task_rules.local_date`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

from personal_agent.domain.models import Task, TaskStatus

STREAK_THRESHOLD_NUM = 4  # score >= 4/5, kept as integers so 0.8 is never a float accident
STREAK_THRESHOLD_DEN = 5
MAX_RANGE_DAYS = 62
_MAX_STREAK_LOOKBACK = 3660


@dataclass(frozen=True, slots=True)
class DaySummary:
    planned: int = 0
    done: int = 0
    achieved: int = 0
    partial: int = 0
    missed: int = 0
    skipped: int = 0
    open: int = 0

    @property
    def score(self) -> float | None:
        return score_of(self.achieved, self.partial, self.planned - self.skipped)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["score"] = self.score
        return data

    @property
    def counts_for_streak(self) -> bool:
        return counts_for_streak(self)

    def __add__(self, other: DaySummary) -> DaySummary:
        return DaySummary(
            *(getattr(self, f) + getattr(other, f) for f in self.__dataclass_fields__)
        )


def score_of(achieved: int, partial: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((achieved + 0.5 * partial) / denominator, 4)


def effective_outcome(task: Task) -> str | None:
    """Stored outcome, or the one implied by a closed legacy task (done -> achieved)."""
    if task.outcome:
        return task.outcome
    if task.status is TaskStatus.DONE:
        return "achieved"
    if task.status is TaskStatus.CANCELLED:
        return "skipped"
    return None


def summarize(tasks: Iterable[Task]) -> DaySummary:
    planned = achieved = partial = missed = skipped = open_ = 0
    for task in tasks:
        planned += 1
        outcome = effective_outcome(task)
        if task.status in (TaskStatus.PLANNED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED):
            open_ += 1
        elif outcome == "achieved":
            achieved += 1
        elif outcome == "partial":
            partial += 1
        elif outcome == "missed":
            missed += 1
        else:
            skipped += 1
    return DaySummary(
        planned=planned,
        done=achieved + partial,
        achieved=achieved,
        partial=partial,
        missed=missed,
        skipped=skipped,
        open=open_,
    )


def counts_for_streak(summary: DaySummary) -> bool:
    denominator = summary.planned - summary.skipped
    if summary.planned == 0 or summary.open > 0 or denominator <= 0:
        return False
    # (2a + p) / (2 * den) >= 4/5  <=>  5 * (2a + p) >= 8 * den
    return STREAK_THRESHOLD_DEN * (2 * summary.achieved + summary.partial) >= (
        2 * STREAK_THRESHOLD_NUM * denominator
    )


def streak_days(by_date: Mapping[date, DaySummary], today: date) -> int:
    """Consecutive counting days ending today, or yesterday while today is still unfinished.

    "Unfinished" means today has open tasks or no tasks yet. A finished today that misses the
    bar (score under 0.8) ends the streak at once.
    """
    current = by_date.get(today)
    if current is None or current.open > 0:
        cursor = today - timedelta(days=1)
    elif counts_for_streak(current):
        cursor = today
    else:
        return 0
    count = 0
    while count < _MAX_STREAK_LOOKBACK:
        summary = by_date.get(cursor)
        if summary is None or not counts_for_streak(summary):
            break
        count += 1
        cursor -= timedelta(days=1)
    return count


def period_stats(summaries: Iterable[DaySummary]) -> dict[str, Any]:
    total = DaySummary()
    for item in summaries:
        total = total + item
    return {
        "planned": total.planned,
        "achieved": total.achieved,
        "partial": total.partial,
        "missed": total.missed,
        "rate": total.score,
    }


def week_start(today: date) -> date:
    """Monday of the ISO week containing `today`."""
    return today - timedelta(days=today.weekday())


def month_start(today: date) -> date:
    return today.replace(day=1)


def day_line(summary: DaySummary) -> str:
    """Plain text like 'Today: 4 of 5 done (80%)' built only from the counts."""
    score = summary.score
    pct = f" ({round(score * 100)}%)" if score is not None else ""
    return f"{summary.done} of {summary.planned} done{pct}"


__all__ = [
    "MAX_RANGE_DAYS",
    "DaySummary",
    "counts_for_streak",
    "day_line",
    "effective_outcome",
    "month_start",
    "period_stats",
    "score_of",
    "streak_days",
    "summarize",
    "week_start",
]
