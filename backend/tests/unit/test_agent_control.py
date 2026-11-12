"""Agent control: preset/pause persistence, daily budgets, and the registry pause gate."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.application.services.agent_control_service import AgentControlService
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.exceptions import PermissionDeniedError
from personal_agent.domain.models import ToolCall
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
    OwnerProfileRepositoryImpl,
)
from tests.conftest import make_spy_tool

OWNER = "dashboard"


@pytest.fixture()
def profiles(session_factory) -> ProfileService:
    return ProfileService(OwnerProfileRepositoryImpl(session_factory))


@pytest.fixture()
def control(profiles) -> AgentControlService:
    return AgentControlService(profiles)


def test_defaults_are_ask_first_unpaused_with_budgets(control) -> None:
    state = control.get(OWNER)
    assert state.autonomy_preset == "ask_first"
    assert state.paused is False
    assert state.budgets["commits_used"] == 0
    assert state.budgets["commits_cap"] > 0
    assert state.budgets["proactive_used"] == 0
    assert state.budgets["proactive_cap"] > 0


def test_patch_persists_across_service_instances(session_factory, profiles, control) -> None:
    control.patch(OWNER, autonomy_preset="balanced")
    control.patch(OWNER, paused=True)  # untouched fields stay as they were

    again = AgentControlService(ProfileService(OwnerProfileRepositoryImpl(session_factory)))
    state = again.get(OWNER)
    assert state.autonomy_preset == "balanced"
    assert state.paused is True
    assert again.is_paused(OWNER) is True


def test_patch_rejects_unknown_preset(control) -> None:
    with pytest.raises(ValueError, match="autonomy preset"):
        control.patch(OWNER, autonomy_preset="yolo")
    assert control.get(OWNER).autonomy_preset == "ask_first"


def test_profile_updates_keep_agent_control(profiles, control) -> None:
    control.patch(OWNER, paused=True)
    profiles.update(OWNER, name="Mikias")
    assert control.get(OWNER).paused is True


def test_daily_counters_reset_on_a_new_local_day(profiles) -> None:
    profile = profiles.get(OWNER)
    profile.agent_control = {
        "counters": {"date": "2026-11-12", "commits_used": 4, "proactive_used": 2}
    }
    profiles.save(profile)

    same_day = AgentControlService(profiles, clock=lambda: datetime(2026, 11, 12, 9, tzinfo=UTC))
    assert same_day.get(OWNER).budgets["commits_used"] == 4
    assert same_day.get(OWNER).budgets["proactive_used"] == 2

    next_day = AgentControlService(profiles, clock=lambda: datetime(2026, 11, 13, 9, tzinfo=UTC))
    assert next_day.get(OWNER).budgets["commits_used"] == 0
    assert next_day.get(OWNER).budgets["proactive_used"] == 0


@pytest.fixture()
def gated_registry(session_factory, control) -> ToolRegistryImpl:
    audit = AuditLogImpl(session_factory)
    registry = ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=ApprovalGatewayImpl(repo=ApprovalRepositoryImpl(session_factory), audit=audit),
        audit=audit,
        is_paused=lambda _ctx: control.is_paused(OWNER),
    )
    registry.register_all(
        [
            make_spy_tool("peek", "read"),
            make_spy_tool("draft", "prepare"),
            make_spy_tool("send", "execute"),
            make_spy_tool("wipe", "destructive"),
        ]
    )
    return registry


def test_pause_blocks_every_non_read_tool(gated_registry, control, ctx) -> None:
    control.patch(OWNER, paused=True)
    for name in ("draft", "send", "wipe"):
        with pytest.raises(PermissionDeniedError, match="paused"):
            gated_registry.execute(ToolCall(id=name, name=name, arguments={}), ctx)


def test_pause_still_allows_read_tools(gated_registry, control, ctx) -> None:
    control.patch(OWNER, paused=True)
    result = gated_registry.execute(ToolCall(id="r", name="peek", arguments={}), ctx)
    assert result.ok


def test_resume_restores_prepare_tools(gated_registry, control, ctx) -> None:
    control.patch(OWNER, paused=True)
    control.patch(OWNER, paused=False)
    result = gated_registry.execute(ToolCall(id="d", name="draft", arguments={}), ctx)
    assert result.ok


def test_paused_block_is_audited(gated_registry, control, session_factory, ctx) -> None:
    control.patch(OWNER, paused=True)
    with pytest.raises(PermissionDeniedError):
        gated_registry.execute(ToolCall(id="d", name="draft", arguments={}), ctx)
    events = AuditLogImpl(session_factory).list_recent(events=["tool.paused_blocked"])
    assert len(events) == 1
