"""Task use cases — create, list, transition — with legality enforced in the domain."""

from __future__ import annotations

import logging

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import TaskStatus
from personal_agent.domain.ports import AuditLog, TaskRepository
from personal_agent.domain.task_rules import new_task, transition

logger = logging.getLogger(__name__)


class TaskService:
    """Task-facing service used by CLI today, by any other interface tomorrow."""

    def __init__(self, repository: TaskRepository, audit: AuditLog | None = None) -> None:
        self._repository = repository
        self._audit = audit

    def create(self, title: str, description: str = "", owner_user_id: str = "default") -> str:
        """Create a task and return its id; nothing asked of any implementation."""
        task = new_task(owner_user_id=owner_user_id, title=title, description=description)
        self._repository.add(task)
        if self._audit is not None:
            self._audit.record(
                "task.created",
                owner_user_id,
                {"task_id": task.id, "title": task.title},
            )
        logger.info("Created task %s for user %s.", task.id, owner_user_id)
        return task.id

    def get(self, task_id: str):
        """Fetch a task; None means not found (interfaces render this cleanly)."""
        return self._repository.get(task_id)

    def list(self, status: TaskStatus | None = None):
        """List tasks, optionally filtered by status."""
        return self._repository.list(status)

    def advance(self, task_id: str, proposed: TaskStatus) -> None:
        """Apply a status change, enforcing the domain's transition rules first."""
        task = self._repository.get(task_id)
        if task is None:
            raise StorageError(f"Cannot advance unknown task id={task_id}.")
        previous_status = task.status
        transition(task, proposed)
        self._repository.save(task)
        if self._audit is not None and task.status != previous_status:
            self._audit.record(
                "task.status_changed",
                task.owner_user_id,
                {
                    "task_id": task.id,
                    "title": task.title,
                    "from": previous_status.value,
                    "to": task.status.value,
                },
            )
        logger.info("Task %s -> %s.", task_id, proposed.value)
