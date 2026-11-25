"""Today's `life` object and the daily nudge texts. Built from real rows only."""

from __future__ import annotations

from typing import Any

from personal_agent.application.services.learn_service import LearnService
from personal_agent.application.services.note_service import NoteService
from personal_agent.application.services.reading_service import ReadingService

NUDGE_KINDS = frozenset({"learning_daily", "reading_daily", "diary_nudge"})


class LifeSummaryService:
    def __init__(self, notes: NoteService, learn: LearnService, reading: ReadingService) -> None:
        self._notes = notes
        self._learn = learn
        self._reading = reading

    def today(self, owner: str) -> dict[str, Any] | None:
        """None when the owner has not used any life module yet."""
        learn = self._learn.stats(owner)
        notes = self._notes.stats(owner)
        reading = self._reading.stats(owner)
        plan = reading["active_plan"]
        if not (
            learn["total"]
            or notes["notes"]
            or notes["diary_entries"]
            or reading["logs"]
            or plan is not None
            or self._reading.list_plans(owner, limit=1)
        ):
            return None
        due = self._learn.due(owner, limit=1)
        recent = self._notes.recent_notes(owner, 3)
        return {
            "learn": {
                "due": learn["due"],
                "total": learn["total"],
                "next_term": due[0].term if due else None,
            },
            "reading": {
                "next": plan.next if plan else None,
                "plan_name": plan.name if plan else None,
                "read_today": reading["read_today"],
                "streak_days": reading["streak_days"],
            },
            "diary": {
                "wrote_today": notes["wrote_diary_today"],
                "streak_days": notes["diary_streak_days"],
            },
            "notes": {
                "recent": [
                    {
                        "id": n.id,
                        "title": n.title or n.body.strip()[:60],
                        "updated_at": n.updated_at.isoformat(),
                    }
                    for n in recent
                ]
            },
        }

    def nudge_text(self, kind: str, owner: str) -> str | None:
        """Factual one-line nudge, or None when there is nothing to nudge about."""
        if kind == "learning_daily":
            stats = self._learn.stats(owner)
            if not stats["due"]:
                return None
            first = self._learn.due(owner, limit=1)
            lead = f' Starting with "{first[0].term}".' if first else ""
            return f"You have {stats['due']} item(s) due for review in Learn.{lead}"
        if kind == "reading_daily":
            reading = self._reading.stats(owner)
            plan = reading["active_plan"]
            if plan is None or reading["read_today"]:
                return None
            return f"Today's reading: {plan.next} ({plan.name})."
        if kind == "diary_nudge":
            if self._notes.stats(owner)["wrote_diary_today"]:
                return None
            return "You have not written in your diary today. A few lines is enough."
        return None
