"""Unit: the agent loop with tool calls, using the offline fake provider."""

from __future__ import annotations

from personal_agent.domain.models import AssistantTurn, Message, ToolCall, ToolContext
from tests.conftest import make_spy_tool


def test_plain_text_turn_returns_final_message(agent, scripted_provider):
    scripted_provider._script = [AssistantTurn(content="Hello there!")]
    outcome = agent.run_turn(
        [Message(role="user", content="hi")],
        ToolContext(user_id="u", session_id="s", origin="cli"),
    )
    assert outcome.final_text == "Hello there!"
    assert outcome.tool_calls_made == []
    assert {m.role for m in outcome.new_messages} == {"assistant"}


def test_tool_call_round_trip(scripted_provider, tool_registry, agent, ctx):
    spy = make_spy_tool("report_time", output="12:00")
    tool_registry.register_all([spy])
    scripted_provider._script = [
        AssistantTurn(tool_calls=(ToolCall(id="c1", name="report_time", arguments={}),)),
        AssistantTurn(content="It is 12:00."),
    ]

    outcome = agent.run_turn([Message(role="user", content="what time?")], ctx)

    assert outcome.final_text == "It is 12:00."
    assert [c.name for c in outcome.tool_calls_made] == ["report_time"]
    roles = [m.role for m in outcome.new_messages]
    assert roles.count("tool") == 1
    tool_message = next(m for m in outcome.new_messages if m.role == "tool")
    assert tool_message.tool_call_id == "c1"
    assert tool_message.content == "12:00"


def test_unknown_tool_is_reported_not_raised(agent, tool_registry, scripted_provider, ctx):
    scripted_provider._script = [
        AssistantTurn(tool_calls=(ToolCall(id="c2", name="does_not_exist", arguments={}),)),
        AssistantTurn(content="Handled."),
    ]
    outcome = agent.run_turn([Message(role="user", content="x")], ctx)
    tool_message = next(m for m in outcome.new_messages if m.role == "tool")
    assert "no tool named" in tool_message.content.lower()


def test_round_budget_stops_runaway_loops(agent, tool_registry, scripted_provider, ctx):
    spy = make_spy_tool("loop_forever")
    tool_registry.register(spy)
    agent._max_tool_rounds = 2
    for _ in range(4):
        scripted_provider._script.append(
            AssistantTurn(tool_calls=(ToolCall(id=f"r{_}", name="loop_forever"),))
        )

    outcome = agent.run_turn([Message(role="user", content="go")], ctx)

    assert "stopped early" in outcome.final_text
