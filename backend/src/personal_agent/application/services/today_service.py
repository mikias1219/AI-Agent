"""Today aggregate (UXC-02): one payload composed from real sources only.

Nothing here invents calendar, email or task facts: an unavailable source yields an empty
list plus an honest connection warning. Active goals come from the goal store; needs-you
merges approvals and suggestions by urgency (at most three).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from personal_agent.application.goal_payloads import goal_payload
from personal_agent.application.services.approval_service import ApprovalService
from personal_agent.application.services.briefing_builder import BriefingDocument
from personal_agent.application.services.goal_service import GoalService
from personal_agent.application.services.inbox_service import InboxService
from personal_agent.application.services.onboarding_service import OnboardingService
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.run_service import RunService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.approvals import ApprovalStatus
from personal_agent.domain.models import AgentRun, Task
from personal_agent.domain.task_rules import TaskView

logger = logging.getLogger(__name__)

NEEDS_YOU_MAX = 3
GOALS_MAX = 5
CALENDAR_UNAVAILABLE = "Calendar is unavailable right now."


class CalendarAgendaService:
    """Next calendar events; honest empty result when Google is not connected."""

    def __init__(
        self,
        *,
        connected: Callable[[], bool],
        fetch: Callable[[int], list[dict[str, Any]]],
    ) -> None:
        self._connected = connected
        self._fetch = fetch

    def get(self, limit: int = 3) -> dict[str, Any]:
        limit = min(max(1, limit), 50)
        if not self._connected():
            return {"connected": False, "events": []}
        try:
            events = self._fetch(limit)
        except Exception as exc:  # noqa: BLE001 — surfaced as an honest error, never fake events
            logger.warning("Calendar agenda unavailable: %s", exc)
            # Keep message short and human — never dump stack traces to the UI.
            detail = str(exc).strip().splitlines()[0][:120] if str(exc).strip() else ""
            message = (
                f"Calendar could not be loaded ({detail})." if detail else CALENDAR_UNAVAILABLE
            )
            return {"connected": True, "events": [], "error": message}
        return {"connected": True, "events": list(events)[:limit]}


class TodayService:
    def __init__(
        self,
        *,
        goals: GoalService | None = None,
        inbox: InboxService | None = None,
        profiles: ProfileService,
        approvals: ApprovalService,
        tasks: TaskService,
        onboarding: OnboardingService,
        runs: RunService,
        agenda: CalendarAgendaService,
        briefing: Callable[[str], BriefingDocument | None],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._goals = goals
        self._inbox = inbox
        self._profiles = profiles
        self._approvals = approvals
        self._tasks = tasks
        self._onboarding = onboarding
        self._runs = runs
        self._agenda = agenda
        self._briefing = briefing
        self._clock = clock or (lambda: datetime.now(UTC))

    def build(self, owner_id: str) -> dict[str, Any]:
        profile = self._profiles.get(owner_id)
        now = self._clock()
        doc = self._briefing(owner_id)
        briefing = (
            doc.to_payload()
            if doc
            else {"text": None, "summary": None, "sections": [], "run_id": None}
        )
        agenda = self._agenda.get(NEEDS_YOU_MAX)
        events = list(agenda.get("events") or [])
        # Briefing is the last stored run; agenda is live. If live fails, reuse briefing
        # calendar items so Today stays coherent instead of "unavailable" + full agenda.
        if not events:
            fallback = _events_from_briefing(briefing)
            if fallback:
                events = fallback[:NEEDS_YOU_MAX]
                if agenda.get("error"):
                    agenda = {**agenda, "error": None}
        active = self._runs.active(owner_id)
        greeting_summary = _safe_greeting_summary(briefing.get("summary"))
        return {
            "greeting": {"name": profile.name, "summary": greeting_summary},
            "needs_you": self._needs_you(owner_id, now),
            "now_next": {
                "events": events,
                "calendar_connected": agenda["connected"],
                "active_run": _active_run_payload(active),
            },
            "plan": {"tasks": self._plan_tasks(owner_id, profile.timezone, now), "plan_id": None},
            "goals": self._active_goals(owner_id),
            "since_last_looked": [],
            "onboarding": self._onboarding.payload(owner_id),
            "connections": {"warnings": _connection_warnings(agenda)},
            "briefing": briefing,
        }

    # -- sections ------------------------------------------------------------

    def _needs_you(self, owner_id: str, now: datetime) -> list[dict[str, Any]]:
        if self._inbox is not None:
            # Approvals and suggestions merged by urgency, capped at three.
            return [
                {k: v for k, v in item.items() if k not in ("approval", "suggestion")}
                for item in self._inbox.open_items(owner_id, NEEDS_YOU_MAX)
            ]
        pending = self._approvals.list_approvals(ApprovalStatus.PENDING, limit=NEEDS_YOU_MAX * 3)
        items = [a for a in pending if not a.is_expired(now)][:NEEDS_YOU_MAX]
        return [
            {
                "kind": "approval",
                "id": a.id,
                "run_id": a.run_id,
                "tool_name": a.tool_name,
                "summary": a.summary,
                "risk": a.risk,
                "untrusted_content": a.untrusted_content,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            }
            for a in items
        ]

    def _active_goals(self, owner_id: str) -> list[dict[str, Any]]:
        if self._goals is None:
            return []
        return [goal_payload(g) for g in list(self._goals.active(owner_id))[:GOALS_MAX]]

    def _plan_tasks(self, owner_id: str, timezone: str, now: datetime) -> list[dict[str, Any]]:
        today = self._tasks.list(
            view=TaskView.TODAY, owner_user_id=owner_id, now=now, timezone=timezone
        )
        return [_task_item(t) for t in today]


def _task_item(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "priority": task.priority.value,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "project": task.project,
    }


def _active_run_payload(run: AgentRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "status": run.status.value,
        "origin": run.origin,
        "input": run.input_text,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def _connection_warnings(agenda: dict[str, Any]) -> list[dict[str, Any]]:
    if not agenda["connected"]:
        return [
            {
                "id": "google",
                "severity": "info",
                "message": "Calendar is not connected.",
                "action": {"label": "Connect", "href": "/connections"},
            }
        ]
    if agenda.get("error"):
        return [
            {
                "id": "google",
                "severity": "warning",
                "message": str(agenda["error"]),
                "action": {"label": "Check connection", "href": "/connections"},
            }
        ]
    return []


def _events_from_briefing(briefing: dict[str, Any]) -> list[dict[str, Any]]:
    """Map stored briefing calendar items into Now/Next event shape."""
    sections = briefing.get("sections") or []
    calendar = next(
        (s for s in sections if isinstance(s, dict) and s.get("id") == "calendar"),
        None,
    )
    if not calendar or calendar.get("status") not in ("ok", "empty"):
        return []
    events: list[dict[str, Any]] = []
    for index, item in enumerate(calendar.get("items") or []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        events.append(
            {
                "id": f"briefing-cal-{index}",
                "title": title,
                "startsAt": str(item.get("time") or ""),
                "location": "",
            }
        )
    return events


def _safe_greeting_summary(raw: object) -> str | None:
    """Keep the Today greeting free of provider dumps and stack noise."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    lowered = text.lower()
    if any(
        marker in lowered
        for marker in (
            "inference http",
            "invalid 'tools",
            "provider returned",
            '"error":',
            "could not finish",
            "briefing sources were gathered",
        )
    ):
        return None
    return text if len(text) <= 280 else text[:277] + "…"
