"""Unit: TaskService update/search/views/reopen/soft-delete and completed_at rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import TaskPriority, TaskStatus
from personal_agent.domain.task_rules import IllegalTaskTransitionError, TaskView
from personal_agent.infrastructure.persistence.repositories import recent_audit

BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 11, 11, 15, 0, tzinfo=BERLIN)


def test_create_with_fields_roundtrips(task_service):
    due = NOW + timedelta(days=1)
    task_id = task_service.create(
        "Pay rent",
        priority=TaskPriority.P1,
        due_at=due,
        project="home",
        tags=["money"],
        source="chat",
    )
    task = task_service.get(task_id)
    assert task.priority is TaskPriority.P1
    assert task.due_at.astimezone(UTC) == due.astimezone(UTC)
    assert (task.project, task.tags, task.source) == ("home", ["money"], "chat")


def test_create_rejects_naive_due(task_service):
    with pytest.raises(ValueError):
        task_service.create("Naive", due_at=datetime(2026, 1, 1))


def test_update_patches_and_clears_fields(task_service, session_factory):
    task_id = task_service.create("Draft", due_at=NOW, project="a")
    updated = task_service.update(task_id, title=" Final ", priority=TaskPriority.P2, due_at=None)
    assert updated.title == "Final"
    stored = task_service.get(task_id)
    assert stored.priority is TaskPriority.P2
    assert stored.due_at is None
    assert stored.project == "a"  # untouched
    events = [e.event for e in recent_audit(session_factory, limit=10)]
    assert "task.updated" in events


def test_update_validates_and_rejects_unknown(task_service):
    task_id = task_service.create("Draft")
    with pytest.raises(ValueError):
        task_service.update(task_id, title="  ")
    with pytest.raises(StorageError):
        task_service.update("missing", title="x")


def test_done_sets_completed_at_and_reopen_clears(task_service):
    task_id = task_service.create("Ship")
    assert task_service.get(task_id).completed_at is None
    task_service.advance(task_id, TaskStatus.DONE)
    assert task_service.get(task_id).completed_at is not None
    reopened = task_service.reopen(task_id)
    assert reopened.status is TaskStatus.PLANNED
    stored = task_service.get(task_id)
    assert stored.status is TaskStatus.PLANNED
    assert stored.completed_at is None


def test_reopen_cancelled_and_reject_open_task(task_service):
    cancelled = task_service.create("Dropped")
    task_service.advance(cancelled, TaskStatus.CANCELLED)
    assert task_service.reopen(cancelled).status is TaskStatus.PLANNED
    with pytest.raises(IllegalTaskTransitionError):
        task_service.reopen(cancelled)  # now planned


def test_soft_delete_hides_by_default(task_service):
    keep = task_service.create("Keep")
    gone = task_service.create("Gone")
    task_service.soft_delete(gone)
    task_service.soft_delete(gone)  # idempotent
    assert [t.id for t in task_service.list()] == [keep]
    assert task_service.get(gone) is None
    assert task_service.get(gone, include_deleted=True).deleted_at is not None
    assert {t.id for t in task_service.list(include_deleted=True)} == {keep, gone}
    assert task_service.search("gone") == []
    assert [t.id for t in task_service.search("gone", include_deleted=True)] == [gone]
    with pytest.raises(StorageError):
        task_service.update(gone, title="nope")
    with pytest.raises(StorageError):
        task_service.soft_delete("missing")


def test_search_matches_title_notes_project_tags(task_service):
    a = task_service.create("Buy Milk", description="organic", project="Groceries")
    b = task_service.create("Call Bob", tags=["phone", "urgent"])
    assert [t.id for t in task_service.search("milk")] == [a]
    assert [t.id for t in task_service.search("ORGANIC groceries")] == [a]
    assert [t.id for t in task_service.search("urgent")] == [b]
    assert task_service.search("   ") == []
    assert task_service.search("zzz") == []


def test_search_respects_owner(task_service):
    mine = task_service.create("Report", owner_user_id="me")
    task_service.create("Report", owner_user_id="other")
    assert [t.id for t in task_service.search("report", owner_user_id="me")] == [mine]


def test_views_today_upcoming_overdue(task_service):
    def mk(title, due):
        return task_service.create(title, due_at=due)

    overdue = mk("overdue", NOW - timedelta(days=1))
    earlier_today = mk("earlier today", NOW.replace(hour=8))
    today = mk("today", NOW.replace(hour=20))
    tomorrow = mk("tomorrow", NOW + timedelta(days=1))
    later = mk("later", NOW + timedelta(days=9))
    no_due = task_service.create("no due")
    done = mk("done", NOW - timedelta(days=3))
    task_service.advance(done, TaskStatus.DONE)
    deleted = mk("deleted", NOW - timedelta(days=2))
    task_service.soft_delete(deleted)

    def ids(view):
        return [
            t.id
            for t in task_service.list(view=view, now=NOW.astimezone(UTC), timezone="Europe/Berlin")
        ]

    assert ids(TaskView.OVERDUE) == [overdue]
    assert ids(TaskView.TODAY) == [earlier_today, today]  # ordered by due date
    assert ids(TaskView.UPCOMING) == [tomorrow, later]
    assert no_due not in ids(TaskView.TODAY)


def test_view_boundary_uses_owner_timezone(task_service):
    # 23:30 UTC Nov 11 is Nov 12 00:30 in Berlin → "today" there, "yesterday" in New York.
    now = datetime(2026, 11, 11, 23, 30, tzinfo=UTC)
    due = datetime(2026, 11, 12, 0, 15, tzinfo=BERLIN)  # Nov 11 23:15 UTC
    task_id = task_service.create("edge", due_at=due)
    berlin = task_service.list(view=TaskView.TODAY, now=now, timezone="Europe/Berlin")
    assert [t.id for t in berlin] == [task_id]
    new_york = task_service.list(view=TaskView.TODAY, now=now, timezone="America/New_York")
    assert [t.id for t in new_york] == [task_id]  # Nov 11 18:15 local, same local day as now
    tokyo = task_service.list(view=TaskView.OVERDUE, now=now, timezone="Asia/Tokyo")
    assert tokyo == []  # Nov 12 08:15 Tokyo, today (Nov 12 08:30) — not overdue
