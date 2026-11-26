"""Habits: check-ins, streaks and the Today habit row (P1-2)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.domain.habits import (
    CHECKIN_STATUSES,
    HABIT_KINDS,
    NOTE_MAX,
    Habit,
    HabitCheckin,
    HabitRepository,
    StreakResult,
    clean_name,
    compute_streak,
    is_due,
)
from personal_agent.domain.life import LifeError
from personal_agent.domain.recurrence import RecurrenceError, parse_rule

_CREATE_FIELDS = {
    "name",
    "kind",
    "rule",
    "recurrence",
    "target_value",
    "target_unit",
    "icon",
    "counts_toward_score",
}
WEEK_DAYS = 7


def _number(value: Any, name: str) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise LifeError(f"{name} must be a number.")
    if value < 0 or value > 1_000_000:
        raise LifeError(f"{name} must be between 0 and 1,000,000.")
    return float(value)


def habit_payload(habit: Habit, streak: StreakResult | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": habit.id,
        "name": habit.name,
        "kind": habit.kind,
        "rule": habit.rule.to_dict(),
        "target_value": habit.target_value,
        "target_unit": habit.target_unit,
        "icon": habit.icon,
        "archived": habit.archived,
        "counts_toward_score": habit.counts_toward_score,
    }
    if streak is not None:
        payload["streak"] = {
            "current": streak.current,
            "best": streak.best,
            "done_last_7": streak.done_last_7,
            "due_last_7": streak.due_last_7,
            "done_last_30": streak.done_last_30,
            "due_last_30": streak.due_last_30,
        }
    return payload


class HabitService:
    def __init__(self, repository: HabitRepository, ctx: LifeContext) -> None:
        self._repo = repository
        self._ctx = ctx

    # -- habits ----------------------------------------------------------------------------

    def create(self, owner: str, data: Mapping[str, Any]) -> Habit:
        unknown = set(data) - _CREATE_FIELDS
        if unknown:
            raise LifeError(f"Unknown field(s): {', '.join(sorted(unknown))}.")
        now = self._ctx.now()
        today = self._ctx.today(owner)
        habit = Habit(
            id=uuid.uuid4().hex,
            owner_user_id=owner,
            name=clean_name(data.get("name")),
            rule=self._rule(data.get("rule") or data.get("recurrence"), today),
            kind=self._kind(data.get("kind", "habit")),
            target_value=_number(data.get("target_value"), "target_value"),
            target_unit=str(data.get("target_unit") or "").strip()[:20],
            icon=str(data.get("icon") or "").strip()[:16],
            counts_toward_score=bool(data.get("counts_toward_score", True)),
            created_at=now,
            updated_at=now,
        )
        self._repo.add(habit)
        self._ctx.record("habit.created", owner, habit_id=habit.id)
        return habit

    def get(self, owner: str, habit_id: str) -> Habit:
        habit = self._repo.get(owner, habit_id)
        if habit is None:
            raise not_found("Habit")
        return habit

    def update(self, owner: str, habit_id: str, data: Mapping[str, Any]) -> Habit:
        habit = self.get(owner, habit_id)
        unknown = set(data) - _CREATE_FIELDS - {"archived"}
        if unknown:
            raise LifeError(f"Unknown field(s): {', '.join(sorted(unknown))}.")
        if "name" in data:
            habit.name = clean_name(data["name"])
        if "kind" in data:
            habit.kind = self._kind(data["kind"])
        if "rule" in data or "recurrence" in data:
            habit.rule = self._rule(data.get("rule") or data.get("recurrence"), habit.rule.start)
        if "target_value" in data:
            habit.target_value = _number(data["target_value"], "target_value")
        if "target_unit" in data:
            habit.target_unit = str(data["target_unit"] or "").strip()[:20]
        if "icon" in data:
            habit.icon = str(data["icon"] or "").strip()[:16]
        if "archived" in data:
            habit.archived = bool(data["archived"])
        if "counts_toward_score" in data:
            habit.counts_toward_score = bool(data["counts_toward_score"])
        habit.updated_at = self._ctx.now()
        self._repo.save(habit)
        self._ctx.record("habit.updated", owner, habit_id=habit.id)
        return habit

    def archive(self, owner: str, habit_id: str) -> Habit:
        return self.update(owner, habit_id, {"archived": True})

    def _kind(self, value: Any) -> str:
        kind = str(value or "habit")
        if kind not in HABIT_KINDS:
            raise LifeError(f"kind must be one of: {', '.join(HABIT_KINDS)}.")
        return kind

    def _rule(self, raw: Any, default_start: date):
        data = dict(raw) if isinstance(raw, Mapping) else {"freq": "daily"}
        try:
            return parse_rule(data, default_start=default_start)
        except RecurrenceError as exc:
            raise LifeError(str(exc)) from exc

    # -- check-ins -------------------------------------------------------------------------

    def check_in(
        self,
        owner: str,
        habit_id: str,
        *,
        day: date | None = None,
        status: str = "done",
        value: float | None = None,
        note: str = "",
    ) -> HabitCheckin:
        habit = self.get(owner, habit_id)
        if status not in CHECKIN_STATUSES:
            raise LifeError(f"status must be one of: {', '.join(CHECKIN_STATUSES)}.")
        today = self._ctx.today(owner)
        target = day or today
        if target > today:
            raise LifeError("You can't check in for a future day.")
        if target < habit.rule.start - timedelta(days=0) and target < today - timedelta(days=366):
            raise LifeError("That day is too far in the past.")
        note = (note or "").strip()
        if len(note) > NOTE_MAX:
            raise LifeError(f"note must be at most {NOTE_MAX} characters.")
        if status == "skipped" and not note:
            raise LifeError("Say why you are skipping (a short note).")
        checkin = self._repo.upsert_checkin(
            HabitCheckin(
                id=uuid.uuid4().hex,
                habit_id=habit.id,
                owner_user_id=owner,
                day=target,
                status=status,
                value=_number(value, "value"),
                note=note,
                created_at=self._ctx.now(),
            )
        )
        self._ctx.record("habit.checked", owner, habit_id=habit.id, status=status)
        return checkin

    def undo_check_in(self, owner: str, habit_id: str, day: date | None = None) -> bool:
        self.get(owner, habit_id)
        return self._repo.delete_checkin(owner, habit_id, day or self._ctx.today(owner))

    # -- views -----------------------------------------------------------------------------

    def habits(self, owner: str, *, include_archived: bool = False) -> Sequence[Habit]:
        return self._repo.list(owner, include_archived=include_archived)

    def with_streaks(self, owner: str) -> list[dict[str, Any]]:
        today = self._ctx.today(owner)
        habits = self._repo.list(owner)
        start = today - timedelta(days=366)
        by_habit: dict[str, list[HabitCheckin]] = {}
        for c in self._repo.checkins(owner, start=start, end=today):
            by_habit.setdefault(c.habit_id, []).append(c)
        return [habit_payload(h, compute_streak(h, by_habit.get(h.id, []), today)) for h in habits]

    def day_status(self, owner: str, day: date | None = None) -> dict[str, Any]:
        """Habits due on `day` with their check-in state: the Today habit row."""
        today = self._ctx.today(owner)
        target = day or today
        habits = [h for h in self._repo.list(owner) if is_due(h, target)]
        checks = {c.habit_id: c for c in self._repo.checkins(owner, start=target, end=target)}
        streaks = {
            item["id"]: item["streak"] for item in self.with_streaks(owner) if "streak" in item
        }
        items = []
        for habit in habits:
            check = checks.get(habit.id)
            items.append(
                {
                    **habit_payload(habit),
                    "status": check.status if check else "open",
                    "value": check.value if check else None,
                    "streak": streaks.get(habit.id),
                }
            )
        done = sum(1 for i in items if i["status"] == "done")
        counted = [i for i in items if i["status"] != "skipped"]
        return {
            "day": target.isoformat(),
            "items": items,
            "done": done,
            "due": len(counted),
            "rate": round(done / len(counted), 3) if counted else None,
        }

    def grid(self, owner: str, *, days: int = WEEK_DAYS) -> dict[str, Any]:
        """Habit grid for the evening review: one cell per habit per day."""
        if not 1 <= days <= 60:
            raise LifeError("days must be between 1 and 60.")
        today = self._ctx.today(owner)
        start = today - timedelta(days=days - 1)
        checks = {
            (c.habit_id, c.day): c.status
            for c in self._repo.checkins(owner, start=start, end=today)
        }
        rows = []
        for habit in self._repo.list(owner):
            cells = []
            for offset in range(days):
                d = start + timedelta(days=offset)
                if not is_due(habit, d):
                    cells.append({"day": d.isoformat(), "state": "off"})
                else:
                    cells.append({"day": d.isoformat(), "state": checks.get((habit.id, d), "open")})
            rows.append({"habit": habit_payload(habit), "cells": cells})
        return {"from": start.isoformat(), "to": today.isoformat(), "rows": rows}

    def day_rate(self, owner: str, day: date) -> tuple[int, int]:
        """(done, due) for the day score; only habits that count toward it."""
        habits = [h for h in self._repo.list(owner) if h.counts_toward_score and is_due(h, day)]
        checks = {c.habit_id: c.status for c in self._repo.checkins(owner, start=day, end=day)}
        due = [h for h in habits if checks.get(h.id) != "skipped"]
        return sum(1 for h in due if checks.get(h.id) == "done"), len(due)

    def nudge_text(self, owner: str) -> str | None:
        """One factual line: habits still open today, plus any missed 3 days running."""
        status = self.day_status(owner)
        open_names = [i["name"] for i in status["items"] if i["status"] == "open"]
        lines: list[str] = []
        if open_names:
            shown = ", ".join(open_names[:3]) + ("…" if len(open_names) > 3 else "")
            lines.append(f"{len(open_names)} habit(s) still open today: {shown}.")
        for habit in self._repo.list(owner):
            if self.missed_streak_days(owner, habit.id, upto=3) >= 3:
                lines.append(f'"{habit.name}" has been missed 3 days running. A smaller target?')
                break
        return " ".join(lines) or None

    def missed_streak_days(self, owner: str, habit_id: str, *, upto: int = 7) -> int:
        """Consecutive scheduled days (ending yesterday) with no check-in (proactive nudges)."""
        habit = self.get(owner, habit_id)
        today = self._ctx.today(owner)
        start = today - timedelta(days=upto)
        checks = {
            c.day for c in self._repo.checkins(owner, start=start, end=today, habit_id=habit_id)
        }
        missed = 0
        for offset in range(1, upto + 1):
            d = today - timedelta(days=offset)
            if not is_due(habit, d):
                continue
            if d in checks:
                break
            missed += 1
        return missed
