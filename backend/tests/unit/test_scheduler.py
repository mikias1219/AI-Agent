"""Scheduler: idempotent tick, late reminders, empty briefing calendar copy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.scheduler_service import SchedulerService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.scheduler import ReminderStatus
from personal_agent.infrastructure.persistence.job_queue import SqlJobQueue
from personal_agent.infrastructure.persistence.repositories import (
    OwnerProfileRepositoryImpl,
    TaskRepositoryImpl,
)
from personal_agent.infrastructure.persistence.scheduler_store import (
    AutomationStoreImpl,
    ReminderStoreImpl,
)


def _scheduler(session_factory, *, clock, telegram=None) -> SchedulerService:
    return SchedulerService(
        jobs=SqlJobQueue(session_factory),
        reminders=ReminderStoreImpl(session_factory),
        automations=AutomationStoreImpl(session_factory),
        tasks=TaskService(TaskRepositoryImpl(session_factory)),
        profiles=ProfileService(OwnerProfileRepositoryImpl(session_factory)),
        telegram_send=telegram,
        clock=clock,
        owner_id="dashboard",
    )


def test_duplicate_tick_delivers_reminder_once(session_factory) -> None:
    sent: list[str] = []
    now = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
    clock = {"t": now}

    def now_fn() -> datetime:
        return clock["t"]

    svc = _scheduler(session_factory, clock=now_fn, telegram=sent.append)
    for auto in svc._automations.list("dashboard"):  # noqa: SLF001
        auto.enabled = False
        svc._automations.save(auto)  # noqa: SLF001
    reminder = svc.create_reminder(
        text="Call Dawit",
        remind_at=now - timedelta(minutes=1),
        owner_user_id="dashboard",
        channels=["telegram", "inbox"],
    )
    first = svc.tick()
    second = svc.tick()
    assert first["processed"] >= 1
    assert second["processed"] == 0
    assert sent == ["Call Dawit"]
    loaded = svc._reminders.get(reminder.id)  # noqa: SLF001
    assert loaded is not None
    assert loaded.status is ReminderStatus.SENT
    assert loaded.late is False


def test_late_label_after_five_minutes(session_factory) -> None:
    sent: list[str] = []
    remind_at = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
    clock = {"t": remind_at}

    def now_fn() -> datetime:
        return clock["t"]

    svc = _scheduler(session_factory, clock=now_fn, telegram=sent.append)
    for auto in svc._automations.list("dashboard"):  # noqa: SLF001
        auto.enabled = False
        svc._automations.save(auto)  # noqa: SLF001
    reminder = svc.create_reminder(
        text="Standup",
        remind_at=remind_at,
        owner_user_id="dashboard",
        channels=["telegram"],
    )
    clock["t"] = remind_at + timedelta(minutes=6)
    svc.tick()
    assert sent == ["[late] Standup"]
    loaded = svc._reminders.get(reminder.id)  # noqa: SLF001
    assert loaded is not None and loaded.late is True


def test_briefing_empty_calendar_copy(session_factory) -> None:
    now = datetime(2026, 11, 12, 8, 5, tzinfo=UTC)
    svc = _scheduler(session_factory, clock=lambda: now)
    automations = svc._automations.list("dashboard")  # noqa: SLF001
    briefing = next(a for a in automations if a.kind == "daily_briefing")
    text, _run_id = svc._build_briefing("dashboard", now)  # noqa: SLF001
    assert "nothing scheduled" in text.lower()
    assert "Pending approvals: none." in text
    result = svc.run_automation_now(briefing.id, "dashboard")
    assert result["processed"] >= 1
    latest = svc.latest_briefing("dashboard")
    assert latest is not None
    assert "nothing scheduled" in latest.lower()


def test_enqueue_idempotency_key(session_factory) -> None:
    jobs = SqlJobQueue(session_factory)
    from personal_agent.domain.scheduler import Job

    now = datetime(2026, 11, 12, tzinfo=UTC)
    a = jobs.enqueue(
        Job(id="a", run_at=now, kind="deliver_reminder", payload={}, idempotency_key="k1")
    )
    b = jobs.enqueue(
        Job(id="b", run_at=now, kind="deliver_reminder", payload={}, idempotency_key="k1")
    )
    assert a.id == b.id
