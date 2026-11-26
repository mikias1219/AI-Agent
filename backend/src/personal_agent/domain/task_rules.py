"""Task domain logic — pure, persistence-free.

State transition rules live here so no repository, service, or interface can promote
a task to an illegal status. Stores and services own *where* tasks are kept; this
module owns *what changes are legal*.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

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


OUTCOMES = ("achieved", "partial", "missed", "skipped")
OPEN_STATUSES = frozenset({TaskStatus.PLANNED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED})
TARGET_UNIT_MAX = 20
OUTCOME_NOTE_MAX = 500
_NUMBER_MAX = 1_000_000_000.0


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
    plan_date: date | None = None,
    target_value: float | None = None,
    target_unit: str = "",
    timezone: str = "UTC",
    now: datetime | None = None,
    recurrence: dict[str, Any] | None = None,
) -> Task:
    """Create a fresh task in PLANNED status with identity and timestamps.

    `plan_date` defaults to the owner-local date of `due_at`, else today in `timezone`.
    """
    if not title.strip():
        raise ValueError("Task title must be a non-empty string.")
    if due_at is not None and due_at.tzinfo is None:
        raise ValueError("due_at must be timezone-aware.")
    now = now or datetime.now(UTC)
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
        plan_date=plan_date if plan_date is not None else default_plan_date(due_at, now, timezone),
        target_value=clean_target_value(target_value),
        target_unit=clean_target_unit(target_unit),
        recurrence=recurrence,
    )


def local_date(moment: datetime, timezone: str = "UTC") -> date:
    """The owner-local calendar date of an instant (DST-aware; naive values read as UTC)."""
    aware = moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
    return aware.astimezone(get_zone(timezone)).date()


def default_plan_date(due_at: datetime | None, now: datetime, timezone: str = "UTC") -> date:
    """The day a task belongs to when none is given: its due date, else today."""
    return local_date(due_at if due_at is not None else now, timezone)


def has_time_of_day(due_at: datetime | None, timezone: str = "UTC") -> bool:
    """Does `due_at` carry a real time of day?

    Date-only phrases resolve to the default 09:00 (and midnight is a date marker), so those
    two wall-clock times count as "date only" and are not pushed to Calendar by default.
    """
    if due_at is None:
        return False
    local = due_at.astimezone(get_zone(timezone))
    return not (local.second == 0 and (local.hour, local.minute) in ((0, 0), (9, 0)))


_VAGUE = frozenset(
    {"hi", "hello", "hey", "test", "testing", "todo", "task", "asdf", "aaa", "ok", "stuff", "thing"}
)


def title_issue(title: str) -> str | None:
    """Why a title is probably not a real task ('hi', one letter, a typo-split word), or None."""
    text = " ".join(title.split()).strip(" .!?")
    if len(text) < 3 or text.lower() in _VAGUE:
        return "Too vague to act on. Rewrite it or delete it."
    if len(set(text.lower())) == 1:
        return "Looks like a typo. Rewrite it or delete it."
    return None


def clean_target_value(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("target_value must be a number.")
    if not 0 < float(value) <= _NUMBER_MAX:
        raise ValueError("target_value must be greater than 0.")
    return float(value)


def clean_actual_value(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("actual_value must be a number.")
    if not 0 <= float(value) <= _NUMBER_MAX:
        raise ValueError("actual_value must be 0 or more.")
    return float(value)


def clean_target_unit(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if len(text) > TARGET_UNIT_MAX:
        raise ValueError(f"target_unit must be at most {TARGET_UNIT_MAX} characters.")
    return text


def clean_outcome_note(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if len(text) > OUTCOME_NOTE_MAX:
        raise ValueError(f"outcome_note must be at most {OUTCOME_NOTE_MAX} characters.")
    return text


def clean_outcome(value: object) -> str:
    text = str(value or "").strip().lower()
    if text not in OUTCOMES:
        raise ValueError(f"outcome must be one of: {', '.join(OUTCOMES)}.")
    return text


def infer_outcome(target: float | None, actual: float | None) -> str:
    """Outcome when the owner did not state one (contract section 7)."""
    if target is None or actual is None:
        return "achieved"
    if actual >= target:
        return "achieved"
    return "partial" if actual > 0 else "missed"


def complete(
    task: Task,
    *,
    outcome: str | None = None,
    actual_value: float | None = None,
    note: str | None = None,
    now: datetime | None = None,
) -> Task:
    """Record what the owner really did. Works on any non-deleted task (also as a correction).

    achieved/partial -> done with `completed_at`; missed/skipped -> cancelled, no completion time.
    """
    moment = now or datetime.now(UTC)
    actual = clean_actual_value(actual_value)
    resolved = (
        clean_outcome(outcome)
        if outcome
        else infer_outcome(task.target_value, actual if actual is not None else task.actual_value)
    )
    note_text = clean_outcome_note(note) if note is not None else None
    if actual is not None:
        task.actual_value = actual
    if note_text is not None:
        task.outcome_note = note_text
    task.outcome = resolved
    if resolved in ("achieved", "partial"):
        task.status = TaskStatus.DONE
        task.completed_at = moment
    else:
        task.status = TaskStatus.CANCELLED
        task.completed_at = None
    task.updated_at = moment
    return task


def transition(task: Task, proposed: TaskStatus, *, now: datetime | None = None) -> Task:
    """Return the same task moved to `proposed`, enforcing legality.

    Entering DONE stamps `completed_at`; leaving DONE clears it. Reopening to PLANNED clears
    `outcome` and `actual_value`. A plain DONE or CANCELLED (no outcome yet) records
    `achieved` or `skipped`, so every closed task has an outcome.
    """
    if task.status == proposed:
        return task  # no-op is always fine
    if not can_transition(task.status, proposed):
        raise IllegalTaskTransitionError(
            f"Illegal task transition {task.status.value} -> {proposed.value} for task "
            f"'{task.title}' ({task.id})."
        )
    previous = task.status
    now = now or datetime.now(UTC)
    task.status = proposed
    task.updated_at = now
    if proposed is TaskStatus.DONE:
        task.completed_at = now
        task.outcome = task.outcome if task.outcome in ("achieved", "partial") else "achieved"
    elif previous is TaskStatus.DONE:
        task.completed_at = None
    if proposed is TaskStatus.CANCELLED:
        task.outcome = task.outcome if task.outcome in ("missed", "skipped") else "skipped"
    if proposed is TaskStatus.PLANNED:
        task.outcome = None
        task.actual_value = None
        task.completed_at = None
    elif proposed in (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED):
        task.outcome = None
    return task


def reopen(task: Task, *, now: datetime | None = None) -> Task:
    """Move a done or cancelled task back to PLANNED, clearing completion and outcome."""
    if task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED):
        raise IllegalTaskTransitionError(
            f"Only done or cancelled tasks can be reopened; '{task.title}' is {task.status.value}."
        )
    transition(task, TaskStatus.PLANNED, now=now)
    task.completed_at = None
    task.outcome = None
    task.actual_value = None
    return task


class TaskView(StrEnum):
    """Named list views over open (not done/cancelled) tasks, by local due date."""

    TODAY = "today"  # due during the current local day
    UPCOMING = "upcoming"  # due from the start of tomorrow onwards
    OVERDUE = "overdue"  # due before the start of the current local day


def _aware(value: datetime) -> datetime:
    """Treat naive datetimes (e.g. read back from SQLite) as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def effective_day(task: Task, timezone: str = "UTC") -> date | None:
    """The owner-local day a task "is on": plan_date wins, else the local date of due_at.

    This is the single day-membership rule shared by Today, Plan, stats and the agent.
    """
    if task.plan_date is not None:
        return task.plan_date
    if task.due_at is None:
        return None
    return _aware(task.due_at).astimezone(get_zone(timezone)).date()


def matches_view(task: Task, view: TaskView, now: datetime, timezone: str = "UTC") -> bool:
    """Does `task` belong in `view` at `now` for the owner's timezone? Views never overlap."""
    if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
        return False
    day = effective_day(task, timezone)
    if day is None:
        return False
    local_today = _aware(now).astimezone(get_zone(timezone)).date()
    if view is TaskView.OVERDUE:
        return day < local_today
    if view is TaskView.TODAY:
        return day == local_today
    return day > local_today
