"""Reminder tools go through the real registry (R2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import DEFAULT_POLICY
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.scheduler_service import SchedulerService
from personal_agent.application.services.task_service import TaskService
from personal_agent.application.tools.builtins.reminders import reminder_tools
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.models import ToolCall, ToolContext
from personal_agent.domain.scheduler import ReminderStatus
from personal_agent.infrastructure.persistence.job_queue import SqlJobQueue
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
    OwnerProfileRepositoryImpl,
    TaskRepositoryImpl,
)
from personal_agent.infrastructure.persistence.scheduler_store import (
    AutomationStoreImpl,
    ReminderStoreImpl,
)


def _stack(session_factory, *, clock):
    audit = AuditLogImpl(session_factory)
    profiles = ProfileService(OwnerProfileRepositoryImpl(session_factory))
    tasks = TaskService(TaskRepositoryImpl(session_factory))
    scheduler = SchedulerService(
        jobs=SqlJobQueue(session_factory),
        reminders=ReminderStoreImpl(session_factory),
        automations=AutomationStoreImpl(session_factory),
        tasks=tasks,
        profiles=profiles,
        audit=audit,
        clock=clock,
        owner_id="dashboard",
    )
    registry = ToolRegistryImpl(
        policy=DEFAULT_POLICY,
        approvals=ApprovalGatewayImpl(repo=ApprovalRepositoryImpl(session_factory), audit=audit),
        audit=audit,
    )
    registry.register_all(reminder_tools(scheduler, profiles))
    return registry, scheduler


def test_reminder_create_only_through_real_tool(session_factory) -> None:
    now = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
    registry, scheduler = _stack(session_factory, clock=lambda: now)
    ctx = ToolContext(user_id="dashboard", session_id="s1", origin="cli")
    result = registry.execute(
        ToolCall(
            id="c1",
            name="reminder_create",
            arguments={"text": "stand up", "in_minutes": 10},
        ),
        ctx,
    )
    assert result.ok
    rows = scheduler.list_reminders("dashboard")
    assert len(rows) == 1
    assert rows[0].text == "stand up"


def test_reminder_late_after_restart(session_factory) -> None:
    remind_at = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
    clock = {"t": remind_at}

    def now_fn() -> datetime:
        return clock["t"]

    registry, scheduler = _stack(session_factory, clock=now_fn)
    for auto in scheduler._automations.list("dashboard"):  # noqa: SLF001
        auto.enabled = False
        scheduler._automations.save(auto)  # noqa: SLF001
    ctx = ToolContext(user_id="dashboard", session_id="s1", origin="cli")
    created = registry.execute(
        ToolCall(
            id="c1",
            name="reminder_create",
            arguments={"text": "Standup", "remind_at": "2026-11-12T09:00:00+00:00"},
        ),
        ctx,
    )
    assert created.ok
    # Simulate process restart: new scheduler/service over same DB, time advanced.
    clock["t"] = remind_at + timedelta(minutes=6)
    _, scheduler2 = _stack(session_factory, clock=now_fn)
    for auto in scheduler2._automations.list("dashboard"):  # noqa: SLF001
        auto.enabled = False
        scheduler2._automations.save(auto)  # noqa: SLF001
    sent: list[str] = []
    scheduler2._telegram_send = sent.append  # noqa: SLF001
    scheduler2.tick()
    assert sent == ["[late] Standup"]
    rows = scheduler2.list_reminders("dashboard", status=ReminderStatus.SENT)
    assert rows and rows[0].late is True
