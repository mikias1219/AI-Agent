import json

import pytest

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.tools.builtins.telegram import telegram_tools
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.exceptions import PermissionDeniedError, ToolInputError
from personal_agent.domain.models import ToolCall
from personal_agent.infrastructure.persistence.repositories import ApprovalRepositoryImpl


class FakeTg:
    def __init__(self):
        self.sent: list[tuple[int, str]] = []

    def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


class _DefaultClient:
    pass


_DEFAULT_CLIENT = _DefaultClient()


def _register(registry, *, client=_DEFAULT_CLIENT, allowed=None, activity=None):
    registry.register_all(
        telegram_tools(
            client=FakeTg() if client is _DEFAULT_CLIENT else client,
            allowed_chat_ids=allowed if allowed is not None else frozenset({1}),
            list_activity=activity if activity is not None else (lambda: []),
        )
    )


def test_send_blocked_when_not_allowlisted(session_factory, ctx, policy, audit_log):
    tg = FakeTg()
    registry = ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory),
            audit=audit_log,
            notifier=lambda _p, _d: "approved",
        ),
        audit=audit_log,
    )
    _register(registry, client=tg, allowed=frozenset({42}))
    with pytest.raises(ToolInputError):
        registry.execute(
            ToolCall(id="1", name="telegram_send_message", arguments={"chat_id": 99, "text": "hi"}),
            ctx,
        )
    assert tg.sent == []


def test_send_requires_approval(tool_registry, ctx):
    _register(tool_registry)
    with pytest.raises(PermissionDeniedError):
        tool_registry.execute(
            ToolCall(id="2", name="telegram_send_message", arguments={"chat_id": 1, "text": "hi"}),
            ctx,
        )


def test_send_ok_when_approved(session_factory, ctx, policy, audit_log):
    tg = FakeTg()
    registry = ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory),
            audit=audit_log,
            notifier=lambda _p, _d: "approved",
        ),
        audit=audit_log,
    )
    _register(registry, client=tg)
    result = registry.execute(
        ToolCall(id="3", name="telegram_send_message", arguments={"chat_id": 1, "text": "hi"}),
        ctx,
    )
    assert result.ok
    assert tg.sent == [(1, "hi")]


def test_send_fails_when_client_missing(session_factory, ctx, policy, audit_log):
    registry = ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory),
            audit=audit_log,
            notifier=lambda _p, _d: "approved",
        ),
        audit=audit_log,
    )
    _register(registry, client=None)
    result = registry.execute(
        ToolCall(id="4", name="telegram_send_message", arguments={"chat_id": 1, "text": "hi"}),
        ctx,
    )
    assert result.ok is False
    assert "configured" in (result.error or "").lower()


def test_list_activity_is_read(tool_registry, ctx):
    rows = [{"event": "telegram.reply_sent", "id": "a"}] * 25
    tool_registry.register_all(
        telegram_tools(
            client=FakeTg(),
            allowed_chat_ids=frozenset({5, 1}),
            list_activity=lambda: rows,
        )
    )
    result = tool_registry.execute(
        ToolCall(id="5", name="telegram_list_activity", arguments={}),
        ctx,
    )
    assert result.ok
    payload = json.loads(result.output)
    assert payload["allowed_chat_ids"] == [1, 5]
    assert len(payload["activity"]) == 20
