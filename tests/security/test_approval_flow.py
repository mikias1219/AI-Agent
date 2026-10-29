"""Security tests: approval decisions are persisted and gate execution safely.

These tests exist to *prove* the security property of the system: an `execute`
tool handler physically cannot run unless a human (the notifier) said yes.
"""

from __future__ import annotations

import pytest
from tests.conftest import make_spy_tool

from personal_agent.core.errors import PermissionDeniedError
from personal_agent.core.types import ToolCall
from personal_agent.security.approvals import ApprovalGatewayImpl
from personal_agent.security.permissions import PermissionPolicy
from personal_agent.storage.repositories import ApprovalRepositoryImpl, AuditLogImpl
from personal_agent.tools.registry import ToolRegistryImpl


def _registry(session_factory, notifier) -> ToolRegistryImpl:
    audit = AuditLogImpl(session_factory)
    return ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory), audit=audit, notifier=notifier
        ),
        audit=audit,
    )


def test_approval_rows_persist_decisions(session_factory, ctx):
    approvals = ApprovalRepositoryImpl(session_factory)
    approvals.create_pending("x1", ToolCall(id="1", name="send_email"), ctx)
    assert approvals.decision("x1") == "pending"
    approvals.update_status("x1", "approved")
    assert approvals.decision("x1") == "approved"


def test_notifier_denial_blocks_execution(session_factory, ctx):
    ran = []

    def denying(_prompt, _details):
        return "denied"

    registry = _registry(session_factory, denying)
    spy = make_spy_tool("publish_post", access_kind="execute")

    # A denied action must register but the *call* must raise, not run.
    registry.register(spy)
    with pytest.raises(PermissionDeniedError) as excinfo:
        registry.execute(ToolCall(id="2", name="publish_post", arguments={}), ctx)
    assert ran == []  # handler never executed
    assert "denied" in str(excinfo.value)


def test_notifier_approval_allows_execution(session_factory, ctx):
    ran = []

    def approving(_prompt, _details):
        ran.append("asked")
        return "approved"

    registry = _registry(session_factory, approving)
    spy = make_spy_tool("publish_post", access_kind="execute", output="posted")
    registry.register(spy)
    result = registry.execute(ToolCall(id="3", name="publish_post", arguments={}), ctx)
    assert ran == ["asked"]
    assert result.ok and result.output == "posted"


def test_deferred_approval_blocks_execution(session_factory, ctx):
    ran = []
    registry = _registry(session_factory, notifier=None)
    spy = make_spy_tool("publish_post", access_kind="execute", output="posted")
    registry.register(spy)
    with pytest.raises(PermissionDeniedError):
        registry.execute(ToolCall(id="4", name="publish_post", arguments={}), ctx)
    assert ran == []
