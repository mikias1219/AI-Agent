"""E2E: ChatService full flow — but with the offline fake provider.

Mirrors what a real CLI session does (same service, same storage), without a
terminal or Ollama, exercising tool calling over two assistant turns.
"""

from __future__ import annotations

from tests.conftest import make_spy_tool

from personal_agent.core.types import AssistantTurn, ToolCall


def test_multi_turn_session_keeps_context(chat_service, scripted_provider, tool_registry):
    tool_registry.register_all([make_spy_tool("get_current_datetime")])
    scripted_provider._script = [
        AssistantTurn(tool_calls=(ToolCall(id="c1", name="get_current_datetime", arguments={}),)),
        AssistantTurn(content="It is time!"),
        AssistantTurn(content="Indeed, later."),
    ]

    session_id, reply1 = chat_service.turn(user_id="u", session_id=None, text="what time is it?")
    _, reply2 = chat_service.turn(user_id="u", session_id=session_id, text="thanks")

    assert reply1 == "It is time!"
    assert reply2 == "Indeed, later."


def test_memory_injected_into_model_context(chat_service, memory_store, scripted_provider):
    """Stored facts reach the model as a system message (not persisted as history)."""
    memory_store.remember("default", "preference", "Prefers bullet answers.")

    _session_id, _ = chat_service.turn(user_id="default", session_id=None, text="hello")

    messages_model_saw = scripted_provider.calls[-1][0]
    assert messages_model_saw[0].role == "system"
    assert "bullet answers" in messages_model_saw[0].content
