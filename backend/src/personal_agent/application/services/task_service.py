"""Task use cases — create, update, search, list views, transition — legality in the domain."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import Task, TaskPriority, TaskStatus
from personal_agent.domain.ports import AuditLog, TaskRepository
from personal_agent.domain.task_rules import (
    TaskView,
    matches_view,
    new_task,
    reopen,
    transition,
)

logger = logging.getLogger(__name__)

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
        onboarding: object | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._onboarding = onboarding

    def _record(self, event: str, task: Task, **extra: Any) -> None:
        if self._audit is not None:
            self._audit.record(
                event, task.owner_user_id, {"task_id": task.id, "title": task.title, **extra}
            )

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
        if changed:
            task.updated_at = datetime.now(UTC)
            self._repository.save(task)
            self._record("task.updated", task, fields=changed)
        return task

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
            moment = now or datetime.now(UTC)
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
        transition(task, proposed)
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
        reopen(task)
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
        now = datetime.now(UTC)
        task.deleted_at = now
        task.updated_at = now
        self._repository.save(task)
        self._record("task.deleted", task)
        logger.info("Soft-deleted task %s.", task_id)
