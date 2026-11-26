"""Weekly and monthly review (P2-4): one read model for the Review tab and the agent."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from personal_agent.application.services.day_service import DayService
from personal_agent.application.services.finance_service import FinanceService
from personal_agent.application.services.habit_service import HabitService
from personal_agent.application.services.time_service import TimeService
from personal_agent.domain.life import LifeError

PERIODS = {"week": 7, "month": 30}


def _rate(done: int, due: int) -> float | None:
    return round(done / due, 3) if due else None


class ReviewService:
    def __init__(
        self, days: DayService, habits: HabitService, finance: FinanceService, time: TimeService
    ) -> None:
        self._time = time
        self._days = days
        self._habits = habits
        self._finance = finance

    def build(self, owner: str, period: str = "week") -> dict[str, Any]:
        if period not in PERIODS:
            raise LifeError("period must be week or month.")
        span = PERIODS[period]
        today = self._days.today(owner)
        start = today - timedelta(days=span - 1)
        prev_start = start - timedelta(days=span)
        current = self._tasks(owner, start, today)
        previous = self._tasks(owner, prev_start, start - timedelta(days=1))
        money = self._finance.totals(owner, start, today)
        money_prev = self._finance.totals(owner, prev_start, start - timedelta(days=1))
        habits = self._habit_rows(owner, span)
        return {
            "period": period,
            "from": start.isoformat(),
            "to": today.isoformat(),
            "tasks": {
                **current["totals"],
                "previous_rate": previous["totals"]["rate"],
                "days": current["days"],
                "missed_tasks": current["missed"][:8],
            },
            "habits": habits,
            "time": self._time.summary(owner, start, today),
            "money": {**money, "previous_spent_minor": money_prev["spent_minor"]},
            "highlights": self._highlights(current, previous, habits, money, money_prev),
        }

    def _tasks(self, owner: str, start: date, end: date) -> dict[str, Any]:
        rows = self._days.range(owner, start, end)
        totals = {
            key: sum(int(r.get(key) or 0) for r in rows)
            for key in ("planned", "achieved", "partial", "missed", "skipped", "open")
        }
        finished = totals["achieved"] + totals["partial"]
        totals["rate"] = _rate(finished, totals["planned"])  # type: ignore[assignment]
        missed: list[dict[str, Any]] = []
        day = start
        while day <= end:
            for task in self._days.tasks_of(owner, day):
                if task.outcome in ("missed", "skipped"):
                    missed.append(
                        {
                            "id": task.id,
                            "title": task.title,
                            "day": day.isoformat(),
                            "outcome": task.outcome,
                            "note": task.outcome_note,
                        }
                    )
            day += timedelta(days=1)
        return {"totals": totals, "days": rows, "missed": missed}

    def _habit_rows(self, owner: str, span: int) -> list[dict[str, Any]]:
        grid = self._habits.grid(owner, days=span)
        out = []
        for row in grid["rows"]:
            states = [c["state"] for c in row["cells"]]
            done = states.count("done")
            due = done + states.count("open")
            out.append(
                {
                    "habit": row["habit"]["name"],
                    "done": done,
                    "due": due,
                    "skipped": states.count("skipped"),
                    "rate": _rate(done, due),
                }
            )
        return out

    @staticmethod
    def _highlights(
        current: dict[str, Any],
        previous: dict[str, Any],
        habits: list[dict[str, Any]],
        money: dict[str, int],
        money_prev: dict[str, int],
    ) -> list[str]:
        """Plain facts only; each line comes straight from the numbers above."""
        notes: list[str] = []
        rate, before = current["totals"]["rate"], previous["totals"]["rate"]
        if rate is not None and before is not None:
            diff = round((rate - before) * 100)
            if diff:
                notes.append(
                    f"Task completion is {'up' if diff > 0 else 'down'} {abs(diff)} points."
                )
        weak = [h for h in habits if h["rate"] is not None and h["rate"] < 0.5]
        if weak:
            notes.append(
                f"Habit to rebuild: {weak[0]['habit']} ({weak[0]['done']}/{weak[0]['due']})."
            )
        strong = [h for h in habits if h["rate"] == 1.0 and h["due"] >= 3]
        if strong:
            notes.append(f"Perfect streak on {strong[0]['habit']}.")
        if money_prev["spent_minor"] and money["spent_minor"] > money_prev["spent_minor"] * 1.2:
            notes.append("Spending is more than 20% above the previous period.")
        if current["totals"]["missed"] >= 3:
            notes.append(f"{current['totals']['missed']} tasks were missed; see the reasons below.")
        return notes
