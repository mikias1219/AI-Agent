"""Daily score read model: tasks, habits, learning, money and reflection in one 0-100 number."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

from personal_agent.application.services.day_service import DayService
from personal_agent.application.services.finance_service import FinanceService
from personal_agent.application.services.habit_service import HabitService
from personal_agent.application.services.learn_service import LearnService
from personal_agent.application.services.life_common import LifeContext
from personal_agent.domain.daily_score import (
    AreaScore,
    clean_weights,
    compute,
    ratio,
    trend,
)
from personal_agent.domain.days import DaySummary, summarize

EVENING_HOUR = 20  # reflection only counts against you once the day is nearly over


class ScoreService:
    def __init__(
        self,
        days: DayService,
        habits: HabitService,
        learn: LearnService,
        finance: FinanceService,
        ctx: LifeContext,
    ) -> None:
        self._days = days
        self._habits = habits
        self._learn = learn
        self._fin = finance
        self._ctx = ctx

    def for_day(
        self, owner: str, day: date | None = None, *, rest: bool = False, weights: Any = None
    ) -> dict[str, Any]:
        today = self._ctx.today(owner)
        target = day or today
        w = clean_weights(weights)
        summary: DaySummary = summarize(self._days.tasks_of(owner, target))
        counted = summary.planned - summary.skipped
        tasks = AreaScore(
            "tasks",
            w["tasks"],
            ratio(summary.achieved + 0.5 * summary.partial, counted),
            f"{summary.achieved} of {counted} tasks done" if counted > 0 else "No tasks planned",
        )
        status = self._habits.day_status(owner, target)
        habits = AreaScore(
            "habits",
            w["habits"],
            ratio(status["done"], status["due"]),
            f"{status['done']} of {status['due']} habits kept"
            if status["due"]
            else "No habits due",
        )
        stats = self._learn.stats(owner)
        reviewed, due = int(stats["reviewed_today"] or 0), int(stats["due"] or 0)
        learning = AreaScore(
            "learning",
            w["learning"],
            ratio(reviewed, reviewed + due) if target == today else None,
            f"{reviewed} words reviewed, {due} still due" if (reviewed + due) else "No words due",
        )
        money = self._money(owner, target, today, w["money"])
        diary = self._days._notes.find_diary(owner, target) is not None  # noqa: SLF001
        late = target < today or self._ctx.now().astimezone(self._zone(owner)).hour >= EVENING_HOUR
        reflection = AreaScore(
            "reflection",
            w["reflection"],
            1.0 if diary else (0.0 if late else None),
            "Diary written" if diary else ("No diary entry" if late else "Write it this evening"),
        )
        result = compute([tasks, habits, learning, money, reflection], rest=rest)
        result["date"] = target.isoformat()
        return result

    def _zone(self, owner: str):
        from personal_agent.domain.dates import get_zone

        return get_zone(self._ctx._profiles.timezone_for(owner))  # noqa: SLF001

    def _money(self, owner: str, target: date, today: date, weight: int) -> AreaScore:
        if target != today:
            return AreaScore("money", weight, None, "Past days are not re-scored for money")
        row = self._fin.today_row(owner)
        left = row.get("left_this_month_minor")
        spent = row["spent_today_minor"]
        if left is None:
            return AreaScore("money", weight, None, "Set a monthly budget to track your allowance")
        days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
        allowance = max(left + spent, 0) // days_left
        if spent <= allowance:
            return AreaScore("money", weight, 1.0, "Spending is within today's allowance")
        return AreaScore(
            "money", weight, ratio(allowance, spent), "Spending is above today's allowance"
        )

    def week(self, owner: str, *, weights: Any = None) -> dict[str, Any]:
        today = self._ctx.today(owner)
        out = []
        for back in range(6, -1, -1):
            day = today - timedelta(days=back)
            score = self.for_day(owner, day, weights=weights)
            out.append({"date": day.isoformat(), "total": score["total"]})
        return {"days": out, **trend([d["total"] for d in out])}
