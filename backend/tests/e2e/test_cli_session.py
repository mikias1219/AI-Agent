"""E2E: ChatService full flow — but with the offline fake provider.

Mirrors what a real CLI session does (same service, same storage), without a
terminal or Ollama, exercising tool calling over two assistant turns.
"""

from __future__ import annotations

from personal_agent.domain.models import AssistantTurn, ToolCall
from personal_agent.infrastructure.persistence.repositories import recent_audit
from tests.conftest import make_spy_tool


def test_multi_turn_session_keeps_context(
    chat_service, scripted_provider, tool_registry, session_factory
):
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
    events = [entry.event for entry in recent_audit(session_factory, limit=20)]
    assert events.count("chat.user_message") == 2
    assert events.count("chat.assistant_response") == 2
    assert "tool.executed" in events


def test_memory_injected_into_model_context(chat_service, memory_store, scripted_provider):
    """Stored facts reach the model as a system message (not persisted as history)."""
    memory_store.remember("default", "preference", "Prefers bullet answers.")

    _session_id, _ = chat_service.turn(user_id="default", session_id=None, text="hello")

    messages_model_saw = scripted_provider.calls[-1][0]
    assert messages_model_saw[0].role == "system"
    assert "bullet answers" in messages_model_saw[0].content


def test_agent_can_create_tasks_via_controlled_tools(tmp_path):
    from personal_agent.app.container import build_app
    from personal_agent.config.settings import Settings
    from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider

    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{tmp_path / 'agent.db'}"})
    provider = FakeProvider(
        [
            AssistantTurn(
                tool_calls=(
                    ToolCall(
                        id="create",
                        name="task_create",
                        arguments={"title": "Try my Telegram agent"},
                    ),
                )
            ),
            AssistantTurn(content="I created your task."),
        ]
    )
    container = build_app(settings=settings, provider=provider)
    _, reply = container.chat.turn(user_id="telegram:42:7", text="Create a task to try my agent.")
    assert reply == "I created your task."
    task = container.tasks.list()[0]
    assert task.title == "Try my Telegram agent"
    assert task.owner_user_id == "telegram:42:7"


def test_development_noop_is_not_advertised_by_production_agent(tmp_path):
    from personal_agent.app.container import build_app
    from personal_agent.config.settings import Settings

    container = build_app(
        settings=Settings.from_env({"DATABASE_URL": f"sqlite:///{tmp_path / 'production.db'}"})
    )
    assert "noop" not in {tool.name for tool in container.registry.specs()}


def test_old_noop_history_is_hidden_from_model_but_not_deleted(
    chat_service, conversations, scripted_provider
):
    from personal_agent.domain.models import Message

    session = conversations.create_session("dashboard")
    conversations.append(
        session, Message(role="assistant", tool_calls=(ToolCall(id="old", name="noop"),))
    )
    conversations.append(
        session, Message(role="tool", name="noop", tool_call_id="old", content="done")
    )
    conversations.append(session, Message(role="assistant", content="Hello."))
    chat_service.turn(user_id="dashboard", session_id=session, text="What can you help with?")
    sent = scripted_provider.calls[-1][0]
    assert not any(m.name == "noop" or any(c.name == "noop" for c in m.tool_calls) for m in sent)
    assert any(m.name == "noop" for m in conversations.load(session))
