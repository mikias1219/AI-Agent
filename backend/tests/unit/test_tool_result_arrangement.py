"""Tool results line up with their calls even when a run was paused for approval."""

from __future__ import annotations

from personal_agent.domain.conversation import PENDING_TOOL_NOTE, arrange_tool_results
from personal_agent.domain.models import Message, ToolCall


def _ask(*ids: str) -> Message:
    return Message(
        role="assistant", tool_calls=tuple(ToolCall(id=i, name=f"tool_{i}") for i in ids)
    )


def _result(call_id: str, text: str = "ok") -> Message:
    return Message(role="tool", content=text, name=f"tool_{call_id}", tool_call_id=call_id)


def test_ordinary_history_is_unchanged():
    history = [
        Message(role="user", content="hi"),
        _ask("a"),
        _result("a"),
        Message(role="assistant", content="done"),
    ]
    assert arrange_tool_results(history) == history


def test_missing_result_gets_a_placeholder_until_the_owner_decides():
    history = [Message(role="user", content="send"), _ask("a", "b"), _result("b", "skipped")]

    arranged = arrange_tool_results(history)

    assert [m.tool_call_id for m in arranged if m.role == "tool"] == ["a", "b"]
    assert arranged[2].content == PENDING_TOOL_NOTE


def test_late_result_moves_next_to_its_call_after_the_owner_chatted_again():
    history = [
        _ask("a"),
        Message(role="user", content="meanwhile, what time is it?"),
        Message(role="assistant", content="noon"),
        _result("a", "sent"),  # stored after the approval was decided
    ]

    arranged = arrange_tool_results(history)

    assert [m.role for m in arranged] == ["assistant", "tool", "user", "assistant"]
    assert arranged[1].content == "sent"


def test_orphan_results_are_dropped():
    assert arrange_tool_results([_result("zzz"), Message(role="user", content="hi")]) == [
        Message(role="user", content="hi")
    ]
