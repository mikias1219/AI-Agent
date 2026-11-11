"""Eval scenario: a runaway tool loop ends with an honest, actionable summary (BR-09, AGT-04).

The scripted model keeps asking for tools. The agent must stop at the limit, report only
what a successful tool result proves, say what remains, and hand control back to the owner.
"""

from __future__ import annotations

from personal_agent.domain.models import AssistantTurn, Message, ToolCall
from tests.conftest import make_spy_tool


def test_runaway_loop_ends_with_honest_summary(agent, scripted_provider, tool_registry, ctx):
    tool_registry.register(make_spy_tool("calendar_search", output="3 events found"))
    tool_registry.register(make_spy_tool("email_send_draft", output="ran"))
    scripted_provider._script = [
        AssistantTurn(tool_calls=(ToolCall(id=f"c{i}", name="calendar_search", arguments={}),))
        for i in range(10)
    ]

    outcome = agent.run_turn([Message(role="user", content="Plan my week and email Sam")], ctx)

    assert outcome.stop_reason == "limit_rounds"
    text = outcome.final_text
    assert "6 tool rounds" in text  # BR-09 default
    assert "calendar_search: 3 events found" in text  # proven by a tool result
    assert "email_send_draft" not in text  # nothing is claimed that never ran
    assert "Still to do" in text and "continue" in text.lower()
    assert "please retry" not in text.lower()  # not the old generic failure
