"""Task tools: P1 fields, ownership, timezone-aware due dates, destructive approval gate."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.tools.builtins.tasks import task_tools
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.exceptions import PermissionDeniedError, ToolInputError
from personal_agent.domain.models import ToolCall, ToolContext
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    OwnerProfileRepositoryImpl,
)


@pytest.fixture()
def profiles(session_factory) -> ProfileService:
    return ProfileService(OwnerProfileRepositoryImpl(session_factory))


def _registry(session_factory, audit_log, task_service, profiles, notifier=None):
    registry = ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory), audit=audit_log, notifier=notifier
        ),
        audit=audit_log,
    )
    registry.register_all(task_tools(task_service, profiles))
    return registry


def _run(registry, ctx, name, **arguments):
    result = registry.execute(ToolCall(id="c", name=name, arguments=arguments), ctx)
    assert result.ok, result.error
    return json.loads(result.output or "null")


def test_create_with_p1_fields_uses_owner_timezone(
    session_factory, audit_log, task_service, profiles, ctx
):
    registry = _registry(session_factory, audit_log, task_service, profiles)
    profiles.update(ctx.user_id, timezone="Asia/Tokyo")

    created = _run(
        registry,
        ctx,
        "task_create",
        title="Call bank",
        priority="p2",
        due="2026-12-01T09:00:00",
        project="Money",
        tags=["phone"],
    )

    # 09:00 Tokyo == 00:00 UTC (storage is UTC)
    assert datetime.fromisoformat(created["due_at"]) == datetime(2026, 12, 1, 0, 0, tzinfo=UTC)
    assert (created["priority"], created["project"], created["tags"]) == ("p2", "Money", ["phone"])
    stored = task_service.get(created["id"])
    assert stored is not None and stored.source == "agent"


def test_update_search_reopen_roundtrip(session_factory, audit_log, task_service, profiles, ctx):
    registry = _registry(session_factory, audit_log, task_service, profiles)
    task_id = _run(registry, ctx, "task_create", title="Write report", due="tomorrow")["id"]

    updated = _run(registry, ctx, "task_update", task_id=task_id, priority="p1", project="Work")
    assert (updated["priority"], updated["project"]) == ("p1", "Work")
    assert updated["due_at"] is not None

    cleared = _run(registry, ctx, "task_update", task_id=task_id, due="")
    assert cleared["due_at"] is None

    assert [t["id"] for t in _run(registry, ctx, "task_search", query="report work")] == [task_id]
    assert _run(registry, ctx, "task_search", query="unrelated") == []

    _run(registry, ctx, "task_update_status", task_id=task_id, status="done")
    assert _run(registry, ctx, "task_list", status="done")[0]["id"] == task_id
    assert _run(registry, ctx, "task_reopen", task_id=task_id)["status"] == "planned"


def test_list_views_and_filters(session_factory, audit_log, task_service, profiles, ctx):
    registry = _registry(session_factory, audit_log, task_service, profiles)
    _run(registry, ctx, "task_create", title="A", due="2026-01-01", priority="p1")
    _run(registry, ctx, "task_create", title="B", priority="p3")

    assert [t["title"] for t in _run(registry, ctx, "task_list", view="overdue")] == ["A"]
    assert [t["title"] for t in _run(registry, ctx, "task_list", priority="p3")] == ["B"]
    assert len(_run(registry, ctx, "task_list")) == 2


def test_tools_reject_other_owners_and_bad_input(
    session_factory, audit_log, task_service, profiles, ctx
):
    registry = _registry(session_factory, audit_log, task_service, profiles)
    task_id = _run(registry, ctx, "task_create", title="Mine")["id"]
    other = ToolContext(user_id="intruder", session_id="s", origin="cli")

    for tool, extra in [
        ("task_update", {"title": "x"}),
        ("task_reopen", {}),
        ("task_update_status", {"status": "done"}),
    ]:
        result = registry.execute(
            ToolCall(id="1", name=tool, arguments={"task_id": task_id, **extra}), other
        )
        assert not result.ok and "unavailable" in (result.error or "")
    assert _run(registry, other, "task_list") == []

    with pytest.raises(ToolInputError):
        registry.execute(
            ToolCall(id="2", name="task_create", arguments={"title": "x", "priority": "urgent"}),
            ctx,
        )
    bad_due = registry.execute(
        ToolCall(id="3", name="task_create", arguments={"title": "x", "due": "whenever"}), ctx
    )
    assert not bad_due.ok


def test_delete_is_destructive_and_needs_approval(
    session_factory, audit_log, task_service, profiles, ctx
):
    asked: list[str] = []

    def deny(_prompt, details):
        asked.append(str(details))
        return "denied"

    registry = _registry(session_factory, audit_log, task_service, profiles, notifier=deny)
    spec = next(s for s in registry.specs() if s.name == "task_delete")
    assert spec.access_kind == "destructive"
    task_id = _run(registry, ctx, "task_create", title="Keep me")["id"]

    with pytest.raises(PermissionDeniedError):
        registry.execute(ToolCall(id="d", name="task_delete", arguments={"task_id": task_id}), ctx)
    assert asked and task_service.get(task_id) is not None

    approving = _registry(
        session_factory, audit_log, task_service, profiles, notifier=lambda *_: "approved"
    )
    assert _run(approving, ctx, "task_delete", task_id=task_id) == {"id": task_id, "deleted": True}
    assert task_service.get(task_id) is None
    assert task_service.get(task_id, include_deleted=True) is not None
