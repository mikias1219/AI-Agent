from personal_agent.application.tools.builtins.utility import get_current_datetime
from personal_agent.application.tools.selection import select_tools
from personal_agent.domain.models import Message, ToolSpec


def test_plain_information_does_not_advertise_unneeded_builtin_tools():
    assert (
        select_tools([Message(role="user", content="What is an AI agent?")], [get_current_datetime])
        == []
    )


def test_actions_current_information_and_references_keep_tools():
    for text in [
        "Hello, create a task",
        "What is the date today?",
        "What are my tasks?",
        "What is that?",
        "Create another one",
        "ሰላም",
    ]:
        assert select_tools([Message(role="user", content=text)], [get_current_datetime]) == [
            get_current_datetime
        ]


def test_custom_tools_are_never_removed_by_builtin_optimization():
    custom = ToolSpec("search_reference", "Search a reference", {}, "read", lambda ctx, args: "")
    assert select_tools([Message(role="user", content="What is an AI agent?")], [custom]) == [
        custom
    ]
