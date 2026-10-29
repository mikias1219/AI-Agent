"""Task use cases — create, list, transition — with legality enforced in the domain."""

from __future__ import annotations

import logging

from personal_agent.core.errors import StorageError
from personal_agent.core.ports import TaskRepository
from personal_agent.core.tasks import new_task, transition
from personal_agent.core.types import TaskStatus

logger = logging.getLogger(__name__)


class TaskService:
    """Task-facing service used by CLI today, by any other interface tomorrow."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create(self, title: str, description: str = "", owner_user_id: str = "default") -> str:
        """Create a task and return its id; nothing asked of any implementation."""
        task = new_task(owner_user_id=owner_user_id, title=title, description=description)
        self._repository.add(task)
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
        transition(task, proposed)
        self._repository.save(task)
        logger.info("Task %s -> %s.", task_id, proposed.value)
