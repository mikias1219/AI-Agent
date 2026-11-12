"""Scheduler: idempotent tick, late reminders, real briefing builder."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from personal_agent.application.agent import Agent
from personal_agent.application.run_events import RunStepRecorder
from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import DEFAULT_POLICY
from personal_agent.application.services.briefing_builder import BriefingBuilder
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.scheduler_service import SchedulerService
from personal_agent.application.services.task_service import TaskService
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.models import ToolContext, ToolSpec
from personal_agent.domain.scheduler import ReminderStatus
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.infrastructure.persistence.job_queue import SqlJobQueue
from personal_agent.infrastructure.persistence.repositories import (
    AgentRunRepositoryImpl,
    ApprovalRepositoryImpl,
    AuditLogImpl,
    OwnerProfileRepositoryImpl,
    TaskRepositoryImpl,
)
from personal_agent.infrastructure.persistence.scheduler_store import (
    AutomationStoreImpl,
    ReminderStoreImpl,
)


def _scheduler(
    session_factory,
    *,
    clock,
    telegram=None,
    google_connected: bool = False,
    calendar_items: list[dict[str, Any]] | None = None,
    calendar_error: str | None = None,
    model: str = "fake",
) -> SchedulerService:
    audit = AuditLogImpl(session_factory)
    registry = ToolRegistryImpl(
        policy=DEFAULT_POLICY,
        approvals=ApprovalGatewayImpl(repo=ApprovalRepositoryImpl(session_factory), audit=audit),
        audit=audit,
    )

    def calendar_list(_ctx: ToolContext, _args: dict[str, Any]) -> str:
        if calendar_error:
            raise RuntimeError(calendar_error)
        return json.dumps({"items": calendar_items or [], "page": 1, "page_size": 20, "total": 0})

    def gmail_search(_ctx: ToolContext, _args: dict[str, Any]) -> str:
        return json.dumps({"items": [], "query": "is:unread"})

    registry.register(
        ToolSpec(
            name="google_calendar_list",
            description="List calendar events",
            parameters_schema={"type": "object", "properties": {}},
            access_kind="read",
            handler=calendar_list,
        )
    )
    registry.register(
        ToolSpec(
            name="google_gmail_search",
            description="Search gmail",
            parameters_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            access_kind="read",
            handler=gmail_search,
            untrusted_output=True,
        )
    )
    provider = FakeProvider(script=["Here is your briefing from verified sources."])
    agent = Agent(provider=provider, registry=registry)
    tasks = TaskService(TaskRepositoryImpl(session_factory))
    profiles = ProfileService(OwnerProfileRepositoryImpl(session_factory))
    runs = AgentRunRepositoryImpl(session_factory)
    events = RunStepRecorder(runs)
    builder = BriefingBuilder(
        agent=agent,
        registry=registry,
        tasks=tasks,
        profiles=profiles,
        runs=runs,
        events=events,
        google_connected=lambda: google_connected,
        model_label=model,
    )
    return SchedulerService(
        jobs=SqlJobQueue(session_factory),
        reminders=ReminderStoreImpl(session_factory),
        automations=AutomationStoreImpl(session_factory),
        tasks=tasks,
        profiles=profiles,
        runs=runs,
        telegram_send=telegram,
        clock=clock,
        owner_id="dashboard",
        briefing_builder=builder,
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


def test_briefing_not_connected_says_so(session_factory) -> None:
    now = datetime(2026, 11, 12, 8, 5, tzinfo=UTC)
    svc = _scheduler(session_factory, clock=lambda: now, google_connected=False)
    doc = svc._build_briefing("dashboard", now)  # noqa: SLF001
    assert "Calendar is not connected" in doc.text
    assert "Calendar: nothing scheduled." not in doc.text
    calendar = next(s for s in doc.sections if s.id == "calendar")
    assert calendar.status == "not_connected"
    assert doc.model == "fake"
    assert doc.prompt_version.startswith("briefing_v1@")
    assert doc.run_id
    run = svc._runs.get(doc.run_id)  # noqa: SLF001
    assert run is not None
    assert run.model == "fake"
    assert run.prompt_version.startswith("briefing_v1@")


def test_briefing_lists_connected_calendar_events(session_factory) -> None:
    now = datetime(2026, 11, 12, 8, 5, tzinfo=UTC)
    svc = _scheduler(
        session_factory,
        clock=lambda: now,
        google_connected=True,
        calendar_items=[
            {"id": "1", "title": "Standup", "startsAt": "2026-11-12T09:00:00Z"},
            {"id": "2", "title": "1:1 with Dawit", "startsAt": "2026-11-12T11:00:00Z"},
        ],
        model="fake-test",
    )
    doc = svc._build_briefing("dashboard", now)  # noqa: SLF001
    calendar = next(s for s in doc.sections if s.id == "calendar")
    assert calendar.status == "ok"
    titles = [i.title for i in calendar.items]
    assert titles == ["Standup", "1:1 with Dawit"]
    assert "Standup" in doc.text
    assert "1:1 with Dawit" in doc.text
    assert doc.model == "fake-test"
    steps = svc._runs.list_steps(doc.run_id)  # noqa: SLF001
    assert any(step.name == "google_calendar_list" for step in steps)


def test_briefing_survives_calendar_failure(session_factory) -> None:
    now = datetime(2026, 11, 12, 8, 5, tzinfo=UTC)
    svc = _scheduler(
        session_factory,
        clock=lambda: now,
        google_connected=True,
        calendar_error="calendar API down",
    )
    doc = svc._build_briefing("dashboard", now)  # noqa: SLF001
    calendar = next(s for s in doc.sections if s.id == "calendar")
    assert calendar.status == "error"
    assert "could not be read" in calendar.summary.lower()
    assert next(s for s in doc.sections if s.id == "tasks").status in {"empty", "ok"}
    assert doc.run_id is not None


def test_source_has_no_hardcoded_calendar_line() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "personal_agent"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "Calendar: nothing scheduled." in text:
            offenders.append(str(path))
    assert offenders == [], f"Hard-coded calendar line still present in {offenders}"


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
