"""Integration: real SQLite via repositories — conversation, task, approval, audit."""

from __future__ import annotations

from personal_agent.domain.models import Message, TaskStatus, ToolCall
from personal_agent.domain.task_rules import new_task
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    recent_audit,
)


def test_conversation_roundtrip_with_tool_calls(conversations):
    session_id = conversations.create_session(user_id="alice")
    conversations.append(
        session_id,
        Message(
            role="assistant",
            content="Calling time tool",
            tool_calls=(ToolCall(id="t1", name="get_current_datetime", arguments={}),),
        ),
    )
    conversations.append(session_id, Message(role="tool", content="2026-01-01T00:00:00+00:00"))

    loaded = conversations.load(session_id, limit=10)

    assert [m.role for m in loaded] == ["assistant", "tool"]
    assert loaded[0].tool_calls[0].name == "get_current_datetime"
    assert loaded[1].tool_call_id is None  # tool *results* carry no call spec


def test_task_roundtrip_and_save(tasks_repo):
    task = new_task(owner_user_id="alice", title="Test repo", description="integration")
    tasks_repo.add(task)

    fetched = tasks_repo.get(task.id)
    assert fetched.title == "Test repo"

    fetched.description = "updated"
    tasks_repo.save(fetched)
    assert tasks_repo.get(task.id).description == "updated"

    assert tasks_repo.list(status=TaskStatus.PLANNED)[0].id == task.id
    assert tasks_repo.list() != []


def test_approval_lifecycle(session_factory, ctx):
    approvals = ApprovalRepositoryImpl(session_factory)
    approval_id = "abc123"
    approvals.create_pending(
        approval_id,
        ToolCall(id="c1", name="send_email", arguments={"to": "x@y.z"}),
        ctx,
    )
    assert approvals.decision(approval_id) == "pending"
    approvals.update_status(approval_id, "approved")
    assert approvals.decision(approval_id) == "approved"
    assert approvals.decision("no-such-id") is None


def test_audit_log_append_and_read(session_factory, audit_log, ctx):
    audit_log.record("tool.executed", ctx.user_id, {"tool": "audit_seed"})  # noqa: F841
    audit_log.record("tool.permission_denied", ctx.user_id, {"tool": "nope"})

    rows = recent_audit(session_factory, limit=5)

    assert [r.event for r in reversed(rows)][-2:] == ["tool.executed", "tool.permission_denied"]


def test_database_creates_missing_local_data_directory(tmp_path):
    from personal_agent.infrastructure.persistence.database import create_engine_from_url, init_db

    database = tmp_path / "new" / "data" / "agent.db"
    engine = create_engine_from_url(f"sqlite:///{database}")
    init_db(engine)
    assert database.is_file()
    engine.dispose()
