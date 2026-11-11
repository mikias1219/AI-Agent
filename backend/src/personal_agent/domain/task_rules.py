"""Task domain logic — pure, persistence-free.

State transition rules live here so no repository, service, or interface can promote
a task to an illegal status. Stores and services own *where* tasks are kept; this
module owns *what changes are legal*.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum

from personal_agent.domain.dates import get_zone
from personal_agent.domain.exceptions import AgentError
from personal_agent.domain.models import Task, TaskPriority, TaskStatus


class IllegalTaskTransitionError(AgentError):
    """Raised when a TaskStatus change is not allowed by the domain."""


_ALLOWED: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PLANNED: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELLED}),
    TaskStatus.IN_PROGRESS: frozenset(
        {TaskStatus.PLANNED, TaskStatus.BLOCKED, TaskStatus.DONE, TaskStatus.CANCELLED}
    ),
    TaskStatus.BLOCKED: frozenset(
        {TaskStatus.PLANNED, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED}
    ),
    TaskStatus.DONE: frozenset({TaskStatus.PLANNED}),
    TaskStatus.CANCELLED: frozenset({TaskStatus.PLANNED}),
}


def can_transition(current: TaskStatus, proposed: TaskStatus) -> bool:
    """Is moving from `current` to `proposed` legal?"""
    return proposed in _ALLOWED[current]


def new_task(
    owner_user_id: str,
    title: str,
    description: str = "",
    *,
    priority: TaskPriority = TaskPriority.NONE,
    due_at: datetime | None = None,
    project: str = "",
    tags: list[str] | None = None,
    source: str = "",
    source_ref: str = "",
) -> Task:
    """Create a fresh task in PLANNED status with identity and timestamps."""
    if not title.strip():
        raise ValueError("Task title must be a non-empty string.")
    if due_at is not None and due_at.tzinfo is None:
        raise ValueError("due_at must be timezone-aware.")
    now = datetime.now(UTC)
    return Task(
        id=uuid.uuid4().hex,
        title=title.strip(),
        description=description.strip(),
        status=TaskStatus.PLANNED,
        owner_user_id=owner_user_id,
        created_at=now,
        updated_at=now,
        priority=priority,
        due_at=due_at,
        project=project.strip(),
        tags=list(tags or []),
        source=source,
        source_ref=source_ref,
    )


def transition(task: Task, proposed: TaskStatus) -> Task:
    """Return the same task moved to `proposed`, enforcing legality.

    Entering DONE stamps `completed_at`; leaving DONE clears it.
    """
    if task.status == proposed:
        return task  # no-op is always fine
    if not can_transition(task.status, proposed):
        raise IllegalTaskTransitionError(
            f"Illegal task transition {task.status.value} -> {proposed.value} for task "
            f"'{task.title}' ({task.id})."
        )
    previous = task.status
    now = datetime.now(UTC)
    task.status = proposed
    task.updated_at = now
    if proposed is TaskStatus.DONE:
        task.completed_at = now
    elif previous is TaskStatus.DONE:
        task.completed_at = None
    return task


def reopen(task: Task) -> Task:
    """Move a done or cancelled task back to PLANNED, clearing `completed_at`."""
    if task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED):
        raise IllegalTaskTransitionError(
            f"Only done or cancelled tasks can be reopened; '{task.title}' is {task.status.value}."
        )
    transition(task, TaskStatus.PLANNED)
    task.completed_at = None
    return task


class TaskView(StrEnum):
    """Named list views over open (not done/cancelled) tasks, by local due date."""

    TODAY = "today"  # due during the current local day
    UPCOMING = "upcoming"  # due from the start of tomorrow onwards
    OVERDUE = "overdue"  # due before the start of the current local day


def _aware(value: datetime) -> datetime:
    """Treat naive datetimes (e.g. read back from SQLite) as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def matches_view(task: Task, view: TaskView, now: datetime, timezone: str = "UTC") -> bool:
    """Does `task` belong in `view` at `now` for the owner's timezone? Views never overlap."""
    if task.due_at is None or task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
        return False
    zone = get_zone(timezone)
    local_today = _aware(now).astimezone(zone).date()
    start_today = datetime.combine(local_today, time.min, tzinfo=zone)
    start_tomorrow = datetime.combine(local_today + timedelta(days=1), time.min, tzinfo=zone)
    due = _aware(task.due_at)
    if view is TaskView.OVERDUE:
        return due < start_today
    if view is TaskView.TODAY:
        return start_today <= due < start_tomorrow
    return due >= start_tomorrow
