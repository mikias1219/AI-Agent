"""Matched skills narrow the tool set by tool_groups."""

from __future__ import annotations

from personal_agent.agent.compose import compose_procedures
from personal_agent.agent.loader import clear_caches, list_skills
from personal_agent.application.tools.selection import integration_group, select_tools
from personal_agent.domain.models import ToolSpec


def _spec(name: str) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=name,
        parameters_schema={"type": "object", "properties": {}},
        access_kind="read",
        handler=lambda _ctx, _args: "",
    )


def test_shipped_skills_declare_tool_groups():
    clear_caches()
    skills = {s.name: s for s in list_skills()}
    assert "reminders" in skills["remind-and-follow-up"].tool_groups
    assert "google" in skills["inbox-to-action"].tool_groups
    assert "memory" in skills["remember-me"].tool_groups


def test_select_tools_intersects_skill_groups():
    tools = [
        _spec("reminder_create"),
        _spec("google_gmail_search"),
        _spec("memory_save"),
        _spec("get_current_datetime"),
    ]
    selected = select_tools(
        [],
        tools,
        skill_groups=frozenset({"reminders"}),
    )
    names = {t.name for t in selected}
    assert names == {"reminder_create", "get_current_datetime"}
    assert all(integration_group(t) in {"reminders", "core"} for t in selected)


def test_compose_soft_plan_for_inbox():
    clear_caches()
    composed = compose_procedures("Reply to Sara that I am free Thursday")
    assert any(s.name == "inbox-to-action" for s in composed.skills)
    assert "Soft plan" in composed.text
    assert "google" in composed.tool_groups
