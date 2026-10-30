"""Unit: the registry is the *only* execution gate — policy and schema enforced."""

from __future__ import annotations

import pytest

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.application.tools.builtins.utility import get_current_datetime
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.exceptions import (
    PermissionDeniedError,
    ToolInputError,
    UnknownToolError,
)
from personal_agent.domain.models import ToolCall
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
)
from tests.conftest import make_spy_tool


@pytest.fixture()
def audit_log(session_factory) -> AuditLogImpl:
    return AuditLogImpl(session_factory)


@pytest.fixture()
def registry(session_factory, audit_log, notifier) -> ToolRegistryImpl:
    """Registry bound to a configurable approval notifier (default: none)."""
    return ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory), audit=audit_log, notifier=notifier
        ),
        audit=audit_log,
    )


@pytest.fixture()
def notifier():
    """None = deferred. Tests assign a callable to approve/deny on demand."""
    return None


def test_unknown_tool_rejected(registry, ctx):
    with pytest.raises(UnknownToolError):
        registry.execute(ToolCall(id="a", name="nope", arguments={}), ctx)


def test_read_tool_runs_without_approval(registry, ctx):
    registry.register(get_current_datetime)
    result = registry.execute(ToolCall(id="b", name="get_current_datetime", arguments={}), ctx)
    assert result.ok
    assert "T" in result.output  # ISO-8601 timestamp shape


def test_schema_violation_rejected(registry, ctx):
    registry.register(get_current_datetime)
    with pytest.raises(ToolInputError):
        registry.execute(ToolCall(id="c", name="get_current_datetime", arguments=3), ctx)


def test_denied_policy_never_runs_handler(session_factory, audit_log, ctx):
    spy = make_spy_tool("going_away")
    registry = ToolRegistryImpl(
        policy=PermissionPolicy(denied_tools={"going_away"}),
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory), audit=audit_log
        ),
        audit=audit_log,
    )
    registry.register(spy)
    with pytest.raises(PermissionDeniedError):
        registry.execute(ToolCall(id="d", name="going_away", arguments={}), ctx)


def test_execute_kind_needs_notifier_approval(session_factory, audit_log, ctx):
    approved_calls: list[str] = []

    def approve(prompt: str, details) -> str:
        approved_calls.append(prompt)
        return "approved"

    registry = ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory), audit=audit_log, notifier=approve
        ),
        audit=audit_log,
    )
    registry.register(make_spy_tool("send_email", access_kind="execute", output="queued"))

    result = registry.execute(ToolCall(id="e", name="send_email", arguments={}), ctx)

    assert result.ok and result.output == "queued"
    assert approved_calls and "send_email" in approved_calls[0]


def test_deferred_approval_blocks_execution(session_factory, audit_log, ctx):
    """No notifier → deferred → handler must never run; caller sees the block."""
    registry = ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory), audit=audit_log
        ),
        audit=audit_log,
    )
    registry.register(make_spy_tool("delete_everything", access_kind="execute"))
    with pytest.raises(PermissionDeniedError) as excinfo:
        registry.execute(ToolCall(id="f", name="delete_everything", arguments={}), ctx)
    assert "deferred" in str(excinfo.value)
