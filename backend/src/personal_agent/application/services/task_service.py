"""Task use cases — create, update, search, list views, transition — legality in the domain."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from personal_agent.application.onboarding_marker import OnboardingMarker
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import Task, TaskPriority, TaskStatus
from personal_agent.domain.ports import AuditLog, TaskRepository
from personal_agent.domain.task_rules import (
    OPEN_STATUSES,
    TaskView,
    clean_actual_value,
    clean_outcome,
    clean_outcome_note,
    clean_target_unit,
    clean_target_value,
    complete,
    local_date,
    matches_view,
    new_task,
    reopen,
    transition,
)

logger = logging.getLogger(__name__)


def _instant(value: datetime | None, default: datetime) -> datetime:
    """Sortable aware instant (naive values read as UTC; None sorts by `default`)."""
    moment = value if value is not None else default
    return moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)


UNSET: Any = object()  # sentinel: "leave this field alone" (None means "clear it")
_Tasks = list[Task]
_Tags = list[str]


class TaskService:
    """Task-facing service used by CLI today, by any other interface tomorrow."""

    def __init__(
        self,
        repository: TaskRepository,
        audit: AuditLog | None = None,
        *,
        onboarding: OnboardingMarker | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._onboarding = onboarding
        self._clock = clock or (lambda: datetime.now(UTC))

    def _record(self, event: str, task: Task, **extra: Any) -> None:
        if self._audit is not None:
            self._audit.record(
                event, task.owner_user_id, {"task_id": task.id, "title": task.title, **extra}
            )

    def _record_owner(self, event: str, owner: str, **details: Any) -> None:
        if self._audit is not None:
            self._audit.record(event, owner, dict(details))

    def _require(self, task_id: str, action: str, allow_deleted: bool = False) -> Task:
        task = self._repository.get(task_id)
        if task is None or (task.is_deleted and not allow_deleted):
            raise StorageError(f"Cannot {action} unknown task id={task_id}.")
        return task

    def create(
        self,
        title: str,
        description: str = "",
        owner_user_id: str = "default",
        *,
        priority: TaskPriority = TaskPriority.NONE,
        due_at: datetime | None = None,
        project: str = "",
        tags: _Tags | None = None,
        source: str = "",
        source_ref: str = "",
        plan_date: date | None = None,
        target_value: float | None = None,
        target_unit: str = "",
        timezone: str = "UTC",
    ) -> str:
        """Create a task and return its id; nothing asked of any implementation."""
        task = new_task(
            owner_user_id=owner_user_id,
            title=title,
            description=description,
            priority=priority,
            due_at=due_at,
            project=project,
            tags=tags,
            source=source,
            source_ref=source_ref,
            plan_date=plan_date,
            target_value=target_value,
            target_unit=target_unit,
            timezone=timezone,
            now=self._clock(),
        )
        self._repository.add(task)
        self._record("task.created", task)
        if self._onboarding is not None:
            try:
                self._onboarding.mark(owner_user_id, "created_task")
            except Exception:  # noqa: BLE001
                logger.exception("Could not mark created_task checklist item")
        logger.info("Created task %s for user %s.", task.id, owner_user_id)
        return task.id

    def get(self, task_id: str, include_deleted: bool = False) -> Task | None:
        """Fetch a task; None means not found (or soft-deleted unless asked for)."""
        task = self._repository.get(task_id)
        if task is not None and task.is_deleted and not include_deleted:
            return None
        return task

    def update(
        self,
        task_id: str,
        *,
        title: str = UNSET,
        description: str = UNSET,
        priority: TaskPriority = UNSET,
        due_at: datetime | None = UNSET,
        project: str = UNSET,
        tags: _Tags = UNSET,
        plan_date: date = UNSET,
        target_value: float | None = UNSET,
        target_unit: str = UNSET,
        actual_value: float | None = UNSET,
        outcome_note: str = UNSET,
    ) -> Task:
        """Patch editable fields. Omitted = unchanged; `due_at=None` clears the due date."""
        task = self._require(task_id, "update")
        changed: list[str] = []
        if title is not UNSET:
            if not title.strip():
                raise ValueError("Task title must be a non-empty string.")
            task.title = title.strip()
            changed.append("title")
        if description is not UNSET:
            task.description = description.strip()
            changed.append("description")
        if priority is not UNSET:
            task.priority = TaskPriority(priority)
            changed.append("priority")
        if due_at is not UNSET:
            if due_at is not None and due_at.tzinfo is None:
                raise ValueError("due_at must be timezone-aware.")
            task.due_at = due_at
            changed.append("due_at")
        if project is not UNSET:
            task.project = project.strip()
            changed.append("project")
        if tags is not UNSET:
            task.tags = list(tags)
            changed.append("tags")
        if plan_date is not UNSET:
            task.plan_date = plan_date
            changed.append("plan_date")
        if target_value is not UNSET:
            task.target_value = clean_target_value(target_value)
            changed.append("target_value")
        if target_unit is not UNSET:
            task.target_unit = clean_target_unit(target_unit)
            changed.append("target_unit")
        if actual_value is not UNSET:
            task.actual_value = clean_actual_value(actual_value)
            changed.append("actual_value")
        if outcome_note is not UNSET:
            task.outcome_note = clean_outcome_note(outcome_note)
            changed.append("outcome_note")
        if changed:
            task.updated_at = self._clock()
            self._repository.save(task)
            self._record("task.updated", task, fields=changed)
        return task

    def complete(
        self,
        task_id: str,
        *,
        outcome: str | None = None,
        actual_value: float | None = None,
        note: str | None = None,
    ) -> Task:
        """Record an achievement: achieved/partial -> done, missed/skipped -> cancelled."""
        task = self._require(task_id, "complete")
        previous_status = task.status
        complete(task, outcome=outcome, actual_value=actual_value, note=note, now=self._clock())
        self._repository.save(task)
        self._record(
            "task.completed",
            task,
            outcome=task.outcome,
            **{"from": previous_status.value, "to": task.status.value},
        )
        return task

    def set_outcome(
        self,
        task_id: str,
        outcome: str,
        *,
        actual_value: float | None = None,
        note: str | None = None,
    ) -> Task:
        """PATCH path: stating an outcome closes the task the same way `complete` does."""
        return self.complete(
            task_id, outcome=clean_outcome(outcome), actual_value=actual_value, note=note
        )

    def tasks_on(self, owner_user_id: str, plan_date: date) -> _Tasks:
        """Not-deleted tasks of one day, ordered by due time then creation."""
        return self.tasks_between(owner_user_id, plan_date, plan_date)

    def tasks_between(self, owner_user_id: str, start: date, end: date) -> _Tasks:
        found = [
            t
            for t in self._repository.list(None)
            if not t.is_deleted
            and t.owner_user_id == owner_user_id
            and t.plan_date is not None
            and start <= t.plan_date <= end
        ]
        found.sort(
            key=lambda t: (
                t.plan_date,
                t.due_at is None,
                _instant(t.due_at, datetime.max),
                _instant(t.created_at, datetime.min),
            )
        )
        return found

    def carry_over(self, owner_user_id: str, source: date, target: date) -> _Tasks:
        """Move that day's open tasks (planned, in progress, blocked) to `target`."""
        moved: _Tasks = []
        now = self._clock()
        for task in self.tasks_on(owner_user_id, source):
            if task.status not in OPEN_STATUSES or source == target:
                continue
            task.plan_date = target
            task.updated_at = now
            self._repository.save(task)
            moved.append(task)
        if moved:
            self._record_owner(
                "task.carried_over",
                owner_user_id,
                count=len(moved),
                source=source.isoformat(),
                to=target.isoformat(),
            )
        return moved

    def set_calendar_link(
        self, task_id: str, event_id: str, synced_at: datetime | None = None
    ) -> Task:
        """Remember the Google Calendar event that mirrors this task."""
        task = self._require(task_id, "link calendar event for")
        task.calendar_event_id = event_id
        task.calendar_synced_at = synced_at or self._clock()
        self._repository.save(task)
        return task

    def today_for(self, owner_user_id: str, timezone: str) -> date:
        return local_date(self._clock(), timezone)

    def list(
        self,
        status: TaskStatus | None = None,
        *,
        view: TaskView | None = None,
        owner_user_id: str | None = None,
        include_deleted: bool = False,
        now: datetime | None = None,
        timezone: str = "UTC",
    ) -> _Tasks:
        """List tasks; soft-deleted are excluded by default. Views order by due date."""
        tasks = self._repository.list(status)
        if not include_deleted:
            tasks = [t for t in tasks if not t.is_deleted]
        if owner_user_id is not None:
            tasks = [t for t in tasks if t.owner_user_id == owner_user_id]
        if view is not None:
            moment = now or self._clock()
            tasks = [t for t in tasks if matches_view(t, view, moment, timezone)]
            tasks.sort(key=lambda t: (t.due_at or moment).astimezone(UTC))
        return tasks

    def search(
        self,
        query: str,
        *,
        owner_user_id: str | None = None,
        include_deleted: bool = False,
    ) -> _Tasks:
        """Case-insensitive match of every query word against title, notes, project, tags."""
        words = query.lower().split()
        if not words:
            return []
        results = []
        for task in self.list(owner_user_id=owner_user_id, include_deleted=include_deleted):
            haystack = " ".join([task.title, task.description, task.project, *task.tags]).lower()
            if all(word in haystack for word in words):
                results.append(task)
        return results

    def advance(self, task_id: str, proposed: TaskStatus) -> None:
        """Apply a status change, enforcing the domain's transition rules first."""
        task = self._require(task_id, "advance")
        previous_status = task.status
        transition(task, proposed, now=self._clock())
        self._repository.save(task)
        if task.status != previous_status:
            self._record(
                "task.status_changed", task, **{"from": previous_status.value, "to": proposed.value}
            )
        logger.info("Task %s -> %s.", task_id, proposed.value)

    def reopen(self, task_id: str) -> Task:
        """Return a done/cancelled task to planned and clear its completion time."""
        task = self._require(task_id, "reopen")
        previous_status = task.status
        reopen(task, now=self._clock())
        self._repository.save(task)
        self._record(
            "task.status_changed", task, **{"from": previous_status.value, "to": task.status.value}
        )
        return task

    def soft_delete(self, task_id: str) -> None:
        """Hide a task from default lists without removing it from storage (idempotent)."""
        task = self._require(task_id, "delete", allow_deleted=True)
        if task.is_deleted:
            return
        now = self._clock()
        task.deleted_at = now
        task.updated_at = now
        self._repository.save(task)
        self._record("task.deleted", task)
        logger.info("Soft-deleted task %s.", task_id)
