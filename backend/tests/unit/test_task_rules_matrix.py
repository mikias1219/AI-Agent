"""Unit: exhaustive task status transition matrix (TSK-02)."""

from __future__ import annotations

import pytest

from personal_agent.domain.models import TaskStatus
from personal_agent.domain.task_rules import (
    IllegalTaskTransitionError,
    can_transition,
    new_task,
    transition,
)

ALLOWED = {
    TaskStatus.PLANNED: {TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {
        TaskStatus.PLANNED,
        TaskStatus.BLOCKED,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    },
    TaskStatus.BLOCKED: {TaskStatus.PLANNED, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.DONE: {TaskStatus.PLANNED},
    TaskStatus.CANCELLED: {TaskStatus.PLANNED},
}


@pytest.mark.parametrize("current", list(TaskStatus))
@pytest.mark.parametrize("proposed", list(TaskStatus))
def test_every_pair(current, proposed):
    t = new_task("u", "t")
    t.status = current
    if proposed == current:
        assert transition(t, proposed).status is current
        return
    legal = proposed in ALLOWED[current]
    assert can_transition(current, proposed) is legal
    if legal:
        assert transition(t, proposed).status is proposed
    else:
        with pytest.raises(IllegalTaskTransitionError):
            transition(t, proposed)
