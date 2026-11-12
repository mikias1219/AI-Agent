"""Structured ToolResult fields for chat cards (R4)."""

from __future__ import annotations

import json

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import DEFAULT_POLICY
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.scheduler_service import SchedulerService
from personal_agent.application.services.task_service import TaskService
from personal_agent.application.tools.builtins.reminders import reminder_tools
from personal_agent.application.tools.builtins.tasks import task_tools
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.models import ToolCall, ToolContext
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


def test_task_and_reminder_return_typed_results(session_factory) -> None:
    audit = AuditLogImpl(session_factory)
    tasks = TaskService(TaskRepositoryImpl(session_factory))
    profiles = ProfileService(OwnerProfileRepositoryImpl(session_factory))
    scheduler = SchedulerService(
        jobs=SqlJobQueue(session_factory),
        reminders=ReminderStoreImpl(session_factory),
        automations=AutomationStoreImpl(session_factory),
        tasks=tasks,
        profiles=profiles,
        owner_id="dashboard",
    )
    registry = ToolRegistryImpl(
        policy=DEFAULT_POLICY,
        approvals=ApprovalGatewayImpl(repo=ApprovalRepositoryImpl(session_factory), audit=audit),
        audit=audit,
    )
    registry.register_all(task_tools(tasks, profiles, scheduler=scheduler))
    registry.register_all(reminder_tools(scheduler, profiles))
    ctx = ToolContext(user_id="dashboard", session_id="s", origin="cli")

    created = registry.execute(
        ToolCall(id="1", name="task_create", arguments={"title": "buy milk"}),
        ctx,
    )
    assert created.ok
    assert created.result_type == "task"
    payload = json.loads(created.output)
    assert payload["title"] == "buy milk"
    assert created.id or payload.get("id")

    reminder = registry.execute(
        ToolCall(
            id="2",
            name="reminder_create",
            arguments={"text": "stand", "in_minutes": 5},
        ),
        ctx,
    )
    assert reminder.ok
    assert reminder.result_type == "reminder"
    assert reminder.id
