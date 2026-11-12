"""Offline evaluation harness (OBS-03) against the real ToolRegistry.

Scenarios script FakeProvider turns and expectations. Tools come from the same
builtin factories the container uses, with stubbed Google/web adapters — scenarios
must not declare their own spy tools.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from personal_agent.application.agent import Agent
from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.application.services.memory_service import MemoryService
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.scheduler_service import SchedulerService
from personal_agent.application.services.task_service import TaskService
from personal_agent.application.tools.builtins.google import google_tools
from personal_agent.application.tools.builtins.memory import memory_tools
from personal_agent.application.tools.builtins.reminders import reminder_tools
from personal_agent.application.tools.builtins.tasks import task_tools
from personal_agent.application.tools.builtins.utility import get_current_datetime
from personal_agent.application.tools.builtins.web import web_tools
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.models import AssistantTurn, Message, ToolCall, ToolContext, ToolSpec
from personal_agent.infrastructure.embeddings.local import LocalHashEmbeddingProvider
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.infrastructure.persistence.job_queue import SqlJobQueue
from personal_agent.infrastructure.persistence.memory_store import SqliteMemoryStore
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

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    passed: bool
    errors: tuple[str, ...]


def list_scenario_paths() -> list[Path]:
    return sorted(SCENARIOS_DIR.glob("*.json"))


def load_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class _StubGoogleClient:
    """Offline Google API stand-in for evals."""

    def __init__(self, stubs: dict[str, Any] | None = None) -> None:
        self._stubs = stubs or {}

    def _maybe_fail(self, key: str) -> None:
        fail = self._stubs.get(key, {}).get("fail")
        if fail:
            raise RuntimeError(str(fail))

    def list_gmail(self, *, page: int, page_size: int) -> dict[str, Any]:
        self._maybe_fail("google_gmail_list")
        return self._stubs.get("google_gmail_list", {}).get(
            "data", {"items": [], "page": page, "page_size": page_size, "total": 0}
        )

    def search_gmail(self, *, query: str, max_results: int = 10) -> dict[str, Any]:
        self._maybe_fail("google_gmail_search")
        data = self._stubs.get("google_gmail_search", {}).get("data", {"items": [], "query": query})
        return {"untrusted": True, "notice": "eval", **data}

    def read_gmail(self, *, message_id: str) -> dict[str, Any]:
        self._maybe_fail("google_gmail_read")
        default = {
            "id": message_id,
            "subject": "Hello",
            "from": "sam@example.com",
            "body": "Hi",
            "snippet": "Hi",
        }
        override = self._stubs.get("google_gmail_read", {}).get("data")
        return {"untrusted": True, "notice": "eval", **(override or default)}

    def list_calendar(self, *, page: int, page_size: int) -> dict[str, Any]:
        self._maybe_fail("google_calendar_list")
        return self._stubs.get("google_calendar_list", {}).get(
            "data",
            {
                "items": [{"id": "e1", "title": "standup", "startsAt": "2026-11-13T10:00:00Z"}],
                "page": page,
                "page_size": page_size,
                "total": 1,
            },
        )

    def find_free_slots(
        self, *, time_min: str, time_max: str, duration_minutes: int = 30
    ) -> dict[str, Any]:
        self._maybe_fail("google_calendar_find_free_slots")
        return self._stubs.get("google_calendar_find_free_slots", {}).get(
            "data",
            {"slots": [{"start": "2026-11-17T14:00:00Z", "end": "2026-11-17T14:30:00Z"}]},
        )

    def list_drive(self, *, page: int, page_size: int) -> dict[str, Any]:
        self._maybe_fail("google_drive_list")
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

    def create_gmail_draft(
        self, *, to: str, subject: str, body: str, thread_id: str | None = None
    ) -> dict[str, Any]:
        self._maybe_fail("google_gmail_create_draft")
        return {"id": "d1", "to": to, "subject": subject, "body": body, "thread_id": thread_id}

    def send_gmail(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        self._maybe_fail("google_gmail_send")
        return {"id": "s1", "to": to, "subject": subject, "body": body}

    def reply_gmail(
        self,
        *,
        message_id: str,
        body: str,
        to: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        self._maybe_fail("google_gmail_reply")
        return {"id": "r1", "message_id": message_id, "body": body, "to": to, "subject": subject}

    def create_calendar_event(
        self, *, title: str, starts_at: str, ends_at: str, location: str = ""
    ) -> dict[str, Any]:
        self._maybe_fail("google_calendar_create")
        return {
            "id": "evt1",
            "title": title,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "location": location,
        }

    def update_calendar_event(self, *, event_id: str, **kwargs: Any) -> dict[str, Any]:
        self._maybe_fail("google_calendar_update")
        return {"id": event_id, **kwargs}

    def delete_calendar_event(self, *, event_id: str) -> dict[str, Any]:
        self._maybe_fail("google_calendar_delete_event")
        return {"id": event_id, "deleted": True}


class _AutoApproveGateway:
    """Approves execute/destructive tools immediately (non-gated eval scenarios)."""

    def request(self, call, ctx, *, access_kind: str = "execute", description: str = ""):
        del call, ctx, access_kind, description
        return "approved"

    def claim(self, approval_id: str, call, ctx) -> None:
        del approval_id, call, ctx

    def finish(self, approval_id: str, *, ok: bool, result: str) -> None:
        del approval_id, ok, result


def build_eval_registry(
    session_factory,
    *,
    stubs: dict[str, Any] | None = None,
    require_approval: bool = False,
) -> tuple[ToolRegistryImpl, SchedulerService, TaskService, MemoryService]:
    """Real ToolRegistryImpl with stubbed Google/web — same factories as the container."""
    audit = AuditLogImpl(session_factory)
    repo = ApprovalRepositoryImpl(session_factory)
    approvals = (
        ApprovalGatewayImpl(repo=repo, audit=audit, durable=True)
        if require_approval
        else _AutoApproveGateway()
    )
    registry = ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=approvals,  # type: ignore[arg-type]
        audit=audit,
    )
    tasks = TaskService(TaskRepositoryImpl(session_factory), audit=audit)
    profiles = ProfileService(OwnerProfileRepositoryImpl(session_factory))
    memory_store = SqliteMemoryStore(session_factory, embeddings=LocalHashEmbeddingProvider())
    memories = MemoryService(memory_store, audit=audit)
    jobs = SqlJobQueue(session_factory)
    scheduler = SchedulerService(
        jobs=jobs,
        reminders=ReminderStoreImpl(session_factory),
        automations=AutomationStoreImpl(session_factory),
        tasks=tasks,
        profiles=profiles,
        approvals=repo,
        audit=audit,
        owner_id="tester",
    )

    registry.register(get_current_datetime)
    registry.register_all(task_tools(tasks, profiles, scheduler=scheduler))
    registry.register_all(memory_tools(memories))
    registry.register_all(reminder_tools(scheduler, profiles))
    registry.register_all(google_tools(client=_StubGoogleClient(stubs), tasks=tasks))  # type: ignore[arg-type]

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text=(
                '<a class="result__a" href="https://example.com">Example result</a>'
                if "duckduckgo" in str(request.url)
                else "<html><body>Example page body for evals.</body></html>"
            ),
        )
    )
    registry.register_all(web_tools(http_client=httpx.Client(transport=transport)))
    return registry, scheduler, tasks, memories


def _script_turn(item: dict[str, Any]) -> AssistantTurn:
    if "tool_calls" in item:
        calls = tuple(
            ToolCall(
                id=str(c["id"]),
                name=str(c["name"]),
                arguments=dict(c.get("arguments") or {}),
            )
            for c in item["tool_calls"]
        )
        return AssistantTurn(content=str(item.get("content") or ""), tool_calls=calls)
    return AssistantTurn(content=str(item.get("content") or ""))


def _seed(
    scenario: dict[str, Any],
    tasks: TaskService,
    memories: MemoryService,
    scheduler: SchedulerService,
) -> None:
    from personal_agent.domain.memory import normalize_kind
    from personal_agent.domain.models import Task, TaskPriority, TaskStatus
    from personal_agent.domain.scheduler import Reminder, ReminderStatus
    from personal_agent.infrastructure.persistence.database import session_scope
    from personal_agent.infrastructure.persistence.models import MemoryRow

    seed = dict(scenario.get("seed") or {})
    user_id = str((scenario.get("context") or {}).get("user_id", "tester"))
    for task in seed.get("tasks") or []:
        tasks._repository.add(  # noqa: SLF001 — eval seed with stable ids
            Task(
                id=str(task.get("id") or "t1"),
                owner_user_id=user_id,
                title=str(task["title"]),
                description=str(task.get("description", "")),
                status=TaskStatus(str(task.get("status", "planned"))),
                priority=TaskPriority(str(task.get("priority", "none"))),
            )
        )
    for mem in seed.get("memories") or []:
        memory_id = str(mem.get("id") or "")
        content = str(mem.get("content", "seed"))
        kind = normalize_kind(str(mem.get("kind", "fact")))
        if memory_id:
            store = memories._store  # noqa: SLF001
            with session_scope(store._factory) as session:  # noqa: SLF001
                session.add(
                    MemoryRow(
                        id=memory_id,
                        user_id=user_id,
                        kind=kind,
                        content=content,
                        embedding=store._embeddings.embed(content),  # noqa: SLF001
                    )
                )
        else:
            memories.create(user_id, kind, content)
    for rem in seed.get("reminders") or []:
        minutes = int(rem.get("in_minutes", 30))
        reminder = Reminder(
            id=str(rem.get("id") or "remseed01"),
            owner_user_id=user_id,
            text=str(rem.get("text", "reminder")),
            remind_at=datetime.now(UTC) + timedelta(minutes=minutes),
            status=ReminderStatus.PENDING,
            channels=["inbox"],
            created_at=datetime.now(UTC),
        )
        scheduler._reminders.add(reminder)  # noqa: SLF001


def run_scenario(scenario: dict[str, Any], session_factory) -> ScenarioResult:
    sid = str(scenario["id"])
    errors: list[str] = []
    if scenario.get("tools"):
        errors.append("scenarios must not define spy tools; use the real registry")
        return ScenarioResult(scenario_id=sid, passed=False, errors=tuple(errors))

    expect_preview = dict(scenario.get("expect") or {})
    require_approval = bool(
        scenario.get("require_approval") or expect_preview.get("stop_reason") == "awaiting_approval"
    )
    registry, scheduler, tasks, memories = build_eval_registry(
        session_factory,
        stubs=dict(scenario.get("stubs") or {}),
        require_approval=require_approval,
    )
    _seed(scenario, tasks, memories, scheduler)

    provider = FakeProvider(script=[_script_turn(t) for t in scenario.get("script") or []])
    max_rounds = int(scenario.get("max_tool_rounds", 6))
    agent = Agent(provider=provider, registry=registry, max_tool_rounds=max_rounds)

    ctx_data = dict(scenario.get("context") or {})
    ctx = ToolContext(
        user_id=str(ctx_data.get("user_id", "tester")),
        session_id=str(ctx_data.get("session_id", "sess-eval")),
        origin=str(ctx_data.get("origin", "cli")),
    )
    outcome = agent.run_turn([Message(role="user", content=str(scenario["input"]))], ctx)
    expect = dict(scenario.get("expect") or {})

    made = [c.name for c in outcome.tool_calls_made]
    if "tool_calls" in expect:
        wanted = list(expect["tool_calls"])
        if made != wanted:
            errors.append(f"tool_calls={made!r} expected {wanted!r}")

    for name in expect.get("forbidden_executed") or []:
        if name in made:
            errors.append(f"forbidden tool executed: {name}")

    text = outcome.final_text or ""
    text_l = text.lower()
    for needle in expect.get("text_contains") or []:
        if needle.lower() not in text_l:
            errors.append(f"missing text {needle!r} in {text!r}")
    for needle in expect.get("text_not_contains") or []:
        if needle.lower() in text_l:
            errors.append(f"forbidden text {needle!r} in {text!r}")

    if "stop_reason" in expect:
        wanted_stop = expect["stop_reason"]
        if outcome.stop_reason != wanted_stop:
            errors.append(f"stop_reason={outcome.stop_reason!r} expected {wanted_stop!r}")

    return ScenarioResult(scenario_id=sid, passed=not errors, errors=tuple(errors))


def registered_tool_specs(session_factory) -> list[ToolSpec]:
    registry, _, _, _ = build_eval_registry(session_factory)
    return registry.specs()
