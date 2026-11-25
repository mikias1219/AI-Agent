"""Owner data export and workspace wipe (BR-13)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from personal_agent.application.goal_payloads import goal_payload, plan_payload
from personal_agent.application.services.goal_service import GoalService
from personal_agent.application.services.life_data_service import LifeDataService
from personal_agent.application.services.memory_service import (
    FORGET_CONFIRM_PHRASE,
    MemoryService,
)
from personal_agent.application.services.plan_service import PlanService
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.suggestion_service import SuggestionService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.exceptions import AgentError

WIPE_PHRASE = "WIPE WORKSPACE"
_TOKEN_TTL_SECONDS = 10 * 60


class SyncData(Protocol):
    """Drive links and sync settings: exported and wiped here, never in the owner's Drive."""

    def export(self, owner: str) -> dict[str, Any]: ...

    def wipe(self, owner: str) -> dict[str, int]: ...


class _WorkspaceAudit(Protocol):
    def record(self, event: str, actor: str, details: Mapping[str, Any]) -> None: ...

    def list_recent(
        self, limit: int = 50, offset: int = 0, events: list[str] | None = None
    ) -> list[dict[str, Any]]: ...


@dataclass(slots=True)
class _WipeToken:
    digest: str
    expires_at: float


class WorkspaceDataService:
    """Export a portable JSON snapshot; wipe clears owner workspace content after confirm."""

    def __init__(
        self,
        *,
        secret: str,
        profiles: ProfileService,
        tasks: TaskService,
        memories: MemoryService,
        goals: GoalService,
        plans: PlanService,
        suggestions: SuggestionService,
        life_data: LifeDataService | None = None,
        sync_data: SyncData | None = None,
        audit: _WorkspaceAudit | None = None,
        google_clear: Callable[[], Mapping[str, Any]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._secret = secret
        self._profiles = profiles
        self._tasks = tasks
        self._memories = memories
        self._goals = goals
        self._plans = plans
        self._suggestions = suggestions
        self._life_data = life_data
        self._sync_data = sync_data
        self._audit = audit
        self._google_clear = google_clear
        self._clock = clock or (lambda: datetime.now(UTC))
        self._wipe_token: _WipeToken | None = None

    def export(self, owner_id: str) -> dict[str, Any]:
        now = self._clock()
        profile = self._profiles.get(owner_id)
        payload = {
            "exported_at": now.isoformat(),
            "owner_user_id": owner_id,
            "profile": {
                "name": profile.name,
                "timezone": profile.timezone,
                "language": profile.language,
                "bio": profile.bio,
                "birthday": profile.birthday,
                "notification_prefs": dict(profile.notification_prefs or {}),
                "member_since": profile.created_at.isoformat() if profile.created_at else None,
            },
            "tasks": [_task_dict(t) for t in self._tasks.list(owner_user_id=owner_id)],
            "memories": [
                {
                    "id": m.id,
                    "kind": m.kind,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in self._memories.list(owner_id)
            ],
            "goals": [goal_payload(g) for g in self._goals.list(owner_id)],
            "plans": [plan_payload(p) for p in self._plans.list(owner_id)],
            "suggestions": [
                {
                    "id": s.id,
                    "kind": s.kind,
                    "title": s.title,
                    "reason": s.reason,
                    "source": s.source,
                    "status": s.status,
                    "proposed_action": dict(s.proposed_action),
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in self._suggestions.list(owner_id)
            ],
            "activity": list(self._audit.list_recent(limit=500)) if self._audit else [],
        }
        if self._life_data is not None:
            payload.update(self._life_data.export(owner_id))
        if self._sync_data is not None:
            payload.update(self._sync_data.export(owner_id))
        if self._audit is not None:
            self._audit.record("workspace.exported", owner_id, {})
        return payload

    def issue_wipe_token(self, owner_id: str) -> dict[str, str]:
        token = secrets.token_urlsafe(24)
        digest = hmac.new(self._secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        self._wipe_token = _WipeToken(
            digest=digest, expires_at=time.monotonic() + _TOKEN_TTL_SECONDS
        )
        if self._audit is not None:
            self._audit.record("workspace.wipe_token_issued", owner_id, {})
        return {"token": token, "confirm_phrase": WIPE_PHRASE}

    def wipe(self, owner_id: str, *, token: str, confirm_phrase: str) -> dict[str, Any]:
        if confirm_phrase.strip() != WIPE_PHRASE:
            raise AgentError(f'Type "{WIPE_PHRASE}" exactly to confirm.')
        issued = self._wipe_token
        if issued is None or time.monotonic() > issued.expires_at:
            raise AgentError("Wipe token expired. Request a new one.")
        expected = hmac.new(self._secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, issued.digest):
            raise AgentError("Wipe token is not valid.")
        self._wipe_token = None

        forget = self._memories.issue_forget_token(owner_id)
        deleted = {
            "memories": self._memories.forget_all(
                owner_id,
                token=forget["token"],
                confirm_phrase=FORGET_CONFIRM_PHRASE,
            ),
            "tasks": self._wipe_tasks(owner_id),
            "suggestions": self._wipe_suggestions(owner_id),
            "goals": self._wipe_goals(owner_id),
        }
        if self._life_data is not None:
            deleted.update(self._life_data.wipe(owner_id))
            profile = self._profiles.get(owner_id)
            profile.bio = ""
            profile.birthday = None
            self._profiles.save(profile)
        if self._sync_data is not None:
            deleted.update(self._sync_data.wipe(owner_id))
        google_cleared = False
        if self._google_clear is not None:
            self._google_clear()
            google_cleared = True
        if self._audit is not None:
            self._audit.record(
                "workspace.wiped",
                owner_id,
                {**deleted, "google_cleared": google_cleared},
            )
        return {"wiped": True, "deleted": deleted, "google_cleared": google_cleared}

    def _wipe_tasks(self, owner_id: str) -> int:
        count = 0
        for task in list(self._tasks.list(owner_user_id=owner_id)):
            try:
                self._tasks.soft_delete(task.id)
                count += 1
            except Exception:  # noqa: BLE001
                continue
        return count

    def _wipe_suggestions(self, owner_id: str) -> int:
        count = 0
        for suggestion in list(self._suggestions.open(owner_id)):
            try:
                self._suggestions.dismiss(suggestion.id, owner_id, feedback="workspace wipe")
                count += 1
            except Exception:  # noqa: BLE001
                continue
        return count

    def _wipe_goals(self, owner_id: str) -> int:
        count = 0
        for goal in list(self._goals.list(owner_id)):
            try:
                self._goals.update(goal.id, owner_id, status="done")
                count += 1
            except Exception:  # noqa: BLE001
                continue
        return count


def _task_dict(task: Any) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "priority": task.priority.value if hasattr(task.priority, "value") else str(task.priority),
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "project": task.project,
        "tags": list(task.tags),
        "plan_date": task.plan_date.isoformat() if task.plan_date else None,
        "target_value": task.target_value,
        "target_unit": task.target_unit,
        "actual_value": task.actual_value,
        "outcome": task.outcome,
        "outcome_note": task.outcome_note,
        "calendar_event_id": task.calendar_event_id,
        "calendar_synced_at": (
            task.calendar_synced_at.isoformat() if task.calendar_synced_at else None
        ),
    }


__all__ = ["WIPE_PHRASE", "WorkspaceDataService"]
