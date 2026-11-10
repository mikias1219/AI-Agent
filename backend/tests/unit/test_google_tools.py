import json

import pytest

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.tools.builtins.google import google_tools
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.exceptions import PermissionDeniedError
from personal_agent.domain.models import ToolCall
from personal_agent.infrastructure.integrations.google.session import GoogleNotConnectedError
from personal_agent.infrastructure.persistence.repositories import ApprovalRepositoryImpl


class FakeClient:
    def __init__(self):
        self.sent = None
        self.created = None
        self.updated = None

    def list_gmail(self, *, page, page_size):
        return {"items": [{"id": "1", "subject": "Hi"}], "page": page, "page_size": page_size, "total": 1}

    def list_calendar(self, *, page, page_size):
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

    def list_drive(self, *, page, page_size):
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

    def send_gmail(self, *, to, subject, body):
        self.sent = (to, subject, body)
        return {"id": "m1"}

    def create_calendar_event(self, *, title, starts_at, ends_at, location=""):
        self.created = (title, starts_at, ends_at, location)
        return {"id": "e1"}

    def update_calendar_event(self, *, event_id, title=None, starts_at=None, ends_at=None, location=None):
        self.updated = (event_id, title, starts_at, ends_at, location)
        return {"id": event_id}


class NotConnectedClient(FakeClient):
    def list_gmail(self, *, page, page_size):
        raise GoogleNotConnectedError("Google is not connected. Connect Google under Connections.")


def test_gmail_list_is_read_and_returns_json(tool_registry, ctx):
    client = FakeClient()
    tool_registry.register_all(google_tools(client=client))
    result = tool_registry.execute(
        ToolCall(id="1", name="google_gmail_list", arguments={"page": 1, "page_size": 5}),
        ctx,
    )
    assert result.ok
    assert json.loads(result.output)["items"][0]["subject"] == "Hi"


def test_gmail_send_requires_approval(tool_registry, ctx):
    tool_registry.register_all(google_tools(client=FakeClient()))
    with pytest.raises(PermissionDeniedError):
        tool_registry.execute(
            ToolCall(id="2", name="google_gmail_send", arguments={"to": "a@b.com", "subject": "S", "body": "B"}),
            ctx,
        )


def test_gmail_send_runs_when_approved(session_factory, ctx, policy, audit_log):
    client = FakeClient()
    registry = ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory),
            audit=audit_log,
            notifier=lambda _p, _d: "approved",
        ),
        audit=audit_log,
    )
    registry.register_all(google_tools(client=client))
    result = registry.execute(
        ToolCall(id="3", name="google_gmail_send", arguments={"to": "a@b.com", "subject": "S", "body": "B"}),
        ctx,
    )
    assert result.ok and client.sent == ("a@b.com", "S", "B")


def test_not_connected_returns_failed_tool_result(tool_registry, ctx):
    tool_registry.register_all(google_tools(client=NotConnectedClient()))
    result = tool_registry.execute(
        ToolCall(id="4", name="google_gmail_list", arguments={"page": 1, "page_size": 5}),
        ctx,
    )
    assert not result.ok
    assert "not connected" in result.error.lower()


def test_calendar_create_requires_approval(tool_registry, ctx):
    tool_registry.register_all(google_tools(client=FakeClient()))
    with pytest.raises(PermissionDeniedError):
        tool_registry.execute(
            ToolCall(
                id="5",
                name="google_calendar_create",
                arguments={
                    "title": "Meet",
                    "starts_at": "2025-01-01T10:00:00Z",
                    "ends_at": "2025-01-01T11:00:00Z",
                },
            ),
            ctx,
        )
