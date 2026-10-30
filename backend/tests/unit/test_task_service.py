"""Unit: task domain and service-level transitions."""

from __future__ import annotations

import pytest

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import TaskStatus
from personal_agent.domain.task_rules import IllegalTaskTransitionError
from personal_agent.infrastructure.persistence.repositories import recent_audit


def test_create_returns_new_task(task_service):
    task_id = task_service.create(title="Water the plants", description="weekly")
    task = task_service.get(task_id)
    assert task is not None
    assert task.title == "Water the plants"
    assert task.status is TaskStatus.PLANNED


def test_legal_transitions_chain(task_service, session_factory):
    """planned → in_progress → done is the happy path."""
    task_id = task_service.create(title="Ship the agent")
    task_service.advance(task_id, TaskStatus.IN_PROGRESS)
    task_service.advance(task_id, TaskStatus.DONE)
    assert task_service.get(task_id).status is TaskStatus.DONE
    events = [entry.event for entry in recent_audit(session_factory, limit=10)]
    assert events.count("task.created") == 1
    assert events.count("task.status_changed") == 2


def test_illegal_transition_is_rejected(task_service):
    task_id = task_service.create(title="Skip states")
    with pytest.raises(IllegalTaskTransitionError):
        task_service.advance(task_id, TaskStatus.DONE)  # planned → done illegal


def test_unknown_task_advance_raises(task_service):
    with pytest.raises(StorageError):
        task_service.advance("missing-id", TaskStatus.CANCELLED)


def test_list_filters_by_status(task_service):
    """Service-level listing reflects persisted statuses."""
    active_id = task_service.create(title="Active work")
    task_service.advance(active_id, TaskStatus.IN_PROGRESS)

    statuses = [t.status for t in task_service.list()]
    assert TaskStatus.IN_PROGRESS in statuses
    assert all(t.status is not TaskStatus.DONE for t in task_service.list(TaskStatus.PLANNED))
