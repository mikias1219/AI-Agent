"""Eval scenario: a risky action pauses the run and never claims success (APR-02, BR-03).

The scripted model reads, then asks to send an email, then would claim it was sent. The
agent must run the read, park on the send, skip the rest of the round and stop without
inventing a result: success may only be reported after an approved, executed tool result.
"""

from __future__ import annotations

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.models import AssistantTurn, Message, ToolCall
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
)
from tests.conftest import make_spy_tool


def test_pause_does_not_claim_the_email_was_sent(scripted_provider, session_factory, policy, ctx):
    from personal_agent.application.agent import Agent

    audit = AuditLogImpl(session_factory)
    repo = ApprovalRepositoryImpl(session_factory)
    registry = ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(repo=repo, audit=audit, durable=True),
        audit=audit,
    )
    registry.register(make_spy_tool("calendar_search", output="free on Friday"))
    registry.register(make_spy_tool("email_send", access_kind="execute", output="sent"))
    scripted_provider._script = [
        AssistantTurn(
            tool_calls=(
                ToolCall(id="c1", name="calendar_search", arguments={}),
                ToolCall(id="c2", name="email_send", arguments={}),
                ToolCall(id="c3", name="calendar_search", arguments={}),
            )
        ),
        AssistantTurn(content="Email sent!"),  # must never be asked for
    ]

    outcome = Agent(provider=scripted_provider, registry=registry).run_turn(
        [Message(role="user", content="Email Sam when I'm free")], ctx
    )

    assert outcome.stop_reason == "awaiting_approval"
    assert "approval" in outcome.final_text.lower()
    assert "sent" not in outcome.final_text.lower()
    assert [c.name for c in outcome.tool_calls_made] == ["calendar_search"]
    assert len(outcome.approvals_requested) == 1
    assert len(scripted_provider.calls) == 1  # the model was not asked to continue
    tool_notes = {m.tool_call_id: m.content for m in outcome.new_messages if m.role == "tool"}
    assert "c2" not in tool_notes  # the parked call has no result yet
    assert tool_notes["c3"].startswith("Not run")  # the rest of the round is parked, not run
    assert repo.decision(outcome.approvals_requested[0]) == "pending"
