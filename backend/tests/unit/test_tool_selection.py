"""Tool selection is integration-based and language-agnostic (R3)."""

from personal_agent.application.tools.builtins.utility import get_current_datetime
from personal_agent.application.tools.selection import integration_group, select_tools
from personal_agent.domain.models import Message, ToolSpec


def _spec(name: str) -> ToolSpec:
    return ToolSpec(
        name,
        f"desc {name}",
        {"type": "object", "properties": {}},
        "read",
        lambda c, a: "",
    )


def test_core_always_included_when_connected_emptyish():
    tools = [get_current_datetime, _spec("task_create"), _spec("google_calendar_list")]
    selected = select_tools(
        [Message(role="user", content="hola")],
        tools,
        connected=frozenset({"core"}),
    )
    names = [t.name for t in selected]
    assert "get_current_datetime" in names
    assert "task_create" not in names
    assert "google_calendar_list" not in names


def test_multilingual_inputs_select_same_groups():
    tools = [
        get_current_datetime,
        _spec("task_create"),
        _spec("google_calendar_list"),
        _spec("memory_search"),
    ]
    connected = frozenset({"core", "tasks", "google", "memory"})
    expected = {
        t.name
        for t in select_tools(
            [Message(role="user", content="x")],
            tools,
            connected=connected,
        )
    }
    for text in [
        "What's on my calendar?",
        "¿Qué hay en mi calendario?",
        "Qu'est-ce qu'il y a sur mon calendrier?",
        "ما هو في تقويمي؟",
    ]:
        got = {
            t.name
            for t in select_tools(
                [Message(role="user", content=text)],
                tools,
                connected=connected,
            )
        }
        assert got == expected


def test_integration_group_inference():
    assert integration_group(_spec("task_list")) == "tasks"
    assert integration_group(_spec("reminder_create")) == "reminders"
    assert integration_group(_spec("google_gmail_send")) == "google"
    assert integration_group(get_current_datetime) == "core"


def test_custom_tools_without_prefix_stay_in_core():
    custom = ToolSpec("search_reference", "Search a reference", {}, "read", lambda ctx, args: "")
    assert select_tools([Message(role="user", content="What is an AI agent?")], [custom]) == [
        custom
    ]
