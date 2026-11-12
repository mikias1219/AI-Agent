"""Goals: create, list, update (spec §9.2). Owner-scoped; every change is audited."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.goals import (
    Goal,
    check_goal_status,
    clean_criteria,
    clean_progress,
    clean_title,
)
from personal_agent.domain.ports import AuditLog, GoalRepository


class GoalService:
    def __init__(
        self,
        repository: GoalRepository,
        *,
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    def create(
        self,
        owner_user_id: str,
        title: str,
        *,
        success_criteria: Sequence[str] | None = None,
        next_step: str = "",
        source: str = "owner",
    ) -> Goal:
        now = self._clock()
        goal = Goal(
            id=uuid.uuid4().hex,
            owner_user_id=owner_user_id,
            title=clean_title(title),
            success_criteria=clean_criteria(success_criteria),
            progress=0.0,
            status="active",
            next_step=(next_step or "").strip(),
            created_at=now,
            updated_at=now,
        )
        self._repository.add(goal)
        self._record("goal.created", goal, source=source)
        return goal

    def get(self, goal_id: str, owner_user_id: str) -> Goal:
        goal = self._repository.get(goal_id)
        if goal is None or goal.owner_user_id != owner_user_id:
            raise StorageError(f"Unknown goal '{goal_id}'.")
        return goal

    def list(self, owner_user_id: str, status: str | None = None) -> Sequence[Goal]:
        if status is not None:
            check_goal_status(status)
        return self._repository.list(owner_user_id, status)

    def active(self, owner_user_id: str) -> Sequence[Goal]:
        return self._repository.list(owner_user_id, "active")

    def update(
        self,
        goal_id: str,
        owner_user_id: str,
        *,
        title: str | None = None,
        success_criteria: Sequence[str] | None = None,
        progress: float | None = None,
        status: str | None = None,
        next_step: str | None = None,
    ) -> Goal:
        goal = self.get(goal_id, owner_user_id)
        changed: list[str] = []
        if title is not None:
            goal.title = clean_title(title)
            changed.append("title")
        if success_criteria is not None:
            goal.success_criteria = clean_criteria(success_criteria)
            changed.append("success_criteria")
        if progress is not None:
            goal.progress = clean_progress(progress)
            changed.append("progress")
        if status is not None:
            goal.status = check_goal_status(status)
            changed.append("status")
        if next_step is not None:
            goal.next_step = next_step.strip()
            changed.append("next_step")
        if changed:
            goal.updated_at = self._clock()
            self._repository.save(goal)
            self._record("goal.updated", goal, fields=changed)
        return goal

    def _record(self, event: str, goal: Goal, **details: object) -> None:
        if self._audit is not None:
            self._audit.record(event, goal.owner_user_id, {"goal_id": goal.id, **details})
