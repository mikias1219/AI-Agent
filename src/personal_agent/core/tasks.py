"""Task domain logic — pure, persistence-free.

State transition rules live here so no repository, service, or interface can promote
a task to an illegal status. Stores and services own *where* tasks are kept; this
module owns *what changes are legal*.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from personal_agent.core.errors import AgentError
from personal_agent.core.types import Task, TaskStatus


class IllegalTaskTransitionError(AgentError):
    """Raised when a TaskStatus change is not allowed by the domain."""


_ALLOWED: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PLANNED: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED}),
    TaskStatus.IN_PROGRESS: frozenset({TaskStatus.BLOCKED, TaskStatus.DONE, TaskStatus.CANCELLED}),
    TaskStatus.BLOCKED: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED}),
    TaskStatus.DONE: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


def can_transition(current: TaskStatus, proposed: TaskStatus) -> bool:
    """Is moving from `current` to `proposed` legal?"""
    return proposed in _ALLOWED[current]


def new_task(owner_user_id: str, title: str, description: str = "") -> Task:
    """Create a fresh task in PLANNED status with identity and timestamps."""
    if not title.strip():
        raise ValueError("Task title must be a non-empty string.")
    now = datetime.now(UTC)
    return Task(
        id=uuid.uuid4().hex,
        title=title.strip(),
        description=description.strip(),
        status=TaskStatus.PLANNED,
        owner_user_id=owner_user_id,
        created_at=now,
        updated_at=now,
    )


def transition(task: Task, proposed: TaskStatus) -> Task:
    """Return the same task moved to `proposed`, enforcing legality."""
    if task.status == proposed:
        return task  # no-op is always fine
    if not can_transition(task.status, proposed):
        raise IllegalTaskTransitionError(
            f"Illegal task transition {task.status.value} -> {proposed.value} for task "
            f"'{task.title}' ({task.id})."
        )
    task.status = proposed
    task.updated_at = datetime.now(UTC)
    return task
