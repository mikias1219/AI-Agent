"""JSON shape of a task (contract section 7). Used by routes, days and export."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from personal_agent.domain.models import Task
from personal_agent.domain.task_rules import title_issue


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def task_payload(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "title_issue": title_issue(task.title),
        "description": task.description,
        "notes": task.description,
        "status": task.status.value,
        "owner_user_id": task.owner_user_id,
        "priority": task.priority.value,
        "due_at": _iso(task.due_at),
        "project": task.project,
        "tags": list(task.tags),
        "source": task.source,
        "source_ref": task.source_ref,
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
        "completed_at": _iso(task.completed_at),
        "deleted_at": _iso(task.deleted_at),
        "plan_date": task.plan_date.isoformat() if task.plan_date else None,
        "target_value": task.target_value,
        "target_unit": task.target_unit,
        "actual_value": task.actual_value,
        "outcome": task.outcome,
        "outcome_note": task.outcome_note,
        "calendar_event_id": task.calendar_event_id,
        "calendar_synced_at": _iso(task.calendar_synced_at),
        "recurrence": task.recurrence,
        "parent_id": task.parent_id,
        "blocked_by": list(task.blocked_by),
    }
