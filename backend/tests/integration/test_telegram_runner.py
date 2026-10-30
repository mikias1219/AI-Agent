"""Integration: Telegram adapter, fully offline (httpx MockTransport + fakes).

Covers: token auth errors, long-poll wiring, fail-closed owner gate with audit,
and two full poll→route→reply cycles through the real ChatService.
"""

from __future__ import annotations

import json

import httpx
import pytest

from personal_agent.domain.models import AssistantTurn, ToolCall
from personal_agent.infrastructure.integrations.telegram.client import (
    POLL_TIMEOUT_SECONDS,
    TelegramBotClient,
)
from personal_agent.infrastructure.integrations.telegram.exceptions import (
    TelegramAuthError,
    TelegramError,
    TelegramNetworkError,
)
from personal_agent.infrastructure.integrations.telegram.mapper import parse_updates
from personal_agent.infrastructure.integrations.telegram.runner import (
    TelegramBotRunner,
    build_allowed_chats,
)
from personal_agent.infrastructure.persistence.repositories import recent_audit
from tests.conftest import make_spy_tool

TOKEN = "123:ABC"


def _client(handler) -> TelegramBotClient:
    return TelegramBotClient(
        TOKEN,
        http=httpx.Client(
            base_url="https://api.telegram.org",
            transport=httpx.MockTransport(handler),
        ),
    )


class RecordingClient(TelegramBotClient):
    """Polls from a scripted queue without any network; records sends."""

    def __init__(self, update_batches: list[list[dict]]) -> None:
        super().__init__(TOKEN)
        self._batches = list(update_batches)
        self.sent: list[tuple[int, str]] = []

    def get_updates(self, offset: int) -> list[dict]:
        return self._batches.pop(0) if self._batches else []

    def send_typing(self, chat_id: int) -> None:
        pass  # no real Telegram requests in offline tests

    def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


# -- client ------------------------------------------------------------------


def test_get_rejects_bad_token_as_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"ok": False, "description": "Unauthorized"})

    with pytest.raises(TelegramAuthError):
        _client(handler).get_me()


def test_network_failure_maps_to_integration_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(TelegramNetworkError):
        _client(handler).get_me()


def test_get_updates_sends_offset_and_poll_timeout():
    capture: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capture[request.url.path] = json.loads(request.content.decode())
        return httpx.Response(200, json={"ok": True, "result": []})

    client = _client(handler)
    client.get_updates(offset=3)

    sent = capture["/bot123:ABC/getUpdates"]
    assert sent["offset"] == 3
    assert sent["timeout"] == POLL_TIMEOUT_SECONDS


def test_send_message_goes_out_with_plain_text():
    capture: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capture[request.url.path] = json.loads(request.content.decode())
        return httpx.Response(200, json={"ok": True, "result": {}})

    _client(handler).send_message(42, "hello")

    sent = capture["/bot123:ABC/sendMessage"]
    assert sent["chat_id"] == 42 and sent["text"] == "hello"


def test_not_ok_responses_raise():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "description": "chat not found"})

    with pytest.raises(TelegramError):
        _client(handler).send_message(1, "x")


def test_empty_token_is_rejected_locally():
    with pytest.raises(TelegramError):
        TelegramBotClient("")


# -- bot runner ----------------------------------------------------------------


def test_build_allowed_chats_parses_list():
    assert build_allowed_chats("1, -2 ; 3 , junk,") == {1, -2, 3}
    assert build_allowed_chats("") == frozenset()
    assert build_allowed_chats(None) == frozenset()


def test_owner_gate_fail_closed_and_audited(chat_service, audit_log, session_factory):
    """Unauthorized chat: NO reply sent, audit row written (fail-closed)."""
    client = RecordingClient(
        [
            [
                {
                    "update_id": 1,
                    "message": {"chat": {"id": 999}, "from": {"id": 5}, "text": "?"},
                }
            ]
        ]
    )
    runner = TelegramBotRunner(
        client=client,
        chat_service=chat_service,
        audit=audit_log,
        allowed_chat_ids=frozenset({42}),
    )

    for incoming in parse_updates(client.get_updates(0)):
        runner.route(incoming, {})

    assert client.sent == []  # silently ignored
    events = [row.event for row in recent_audit(session_factory)]
    assert "security.telegram_unauthorized_chat" in events


def test_std_tool_then_text_reply_via_real_service(
    chat_service, tool_registry, scripted_provider, audit_log, session_factory
):
    """Two anon-owner turns: a tool round trip, then a plain reply; others ignored."""
    tool_registry.register_all([make_spy_tool("get_current_datetime")])
    scripted_provider._script = [
        AssistantTurn(tool_calls=(ToolCall(id="t1", name="get_current_datetime", arguments={}),)),
        AssistantTurn(content="It is noon."),
        AssistantTurn(content="Still noon."),
    ]
    client = RecordingClient(
        [
            [
                {
                    "update_id": 1,
                    "message": {"chat": {"id": 42}, "from": {"id": 7}, "text": "time?"},
                },
                {
                    "update_id": 2,
                    "message": {"chat": {"id": 999}, "from": {"id": 7}, "text": "intruder"},
                },
            ],
            [
                {
                    "update_id": 3,
                    "message": {"chat": {"id": 42}, "from": {"id": 7}, "text": "and now?"},
                }
            ],
        ]
    )
    runner = TelegramBotRunner(
        client=client,
        chat_service=chat_service,
        audit=audit_log,
        allowed_chat_ids=frozenset({42}),
    )

    sessions: dict[tuple[int, int], str] = {}
    for incoming in parse_updates(client.get_updates(0)):
        runner.route(incoming, sessions)
    for incoming in parse_updates(client.get_updates(0)):
        runner.route(incoming, sessions)

    assert client.sent[0] == (42, "It is noon.")  # tool round-trip reply
    assert client.sent[-1] == (42, "Still noon.")
    assert all(chat_id == 42 for chat_id, _text in client.sent)
    events = [row.event for row in recent_audit(session_factory, limit=30)]
    assert events.count("telegram.reply_sent") == 2
    assert events.count("chat.user_message") == 2
    assert events.count("chat.assistant_response") == 2


def test_route_maps_sessions_per_chat(chat_service, audit_log):
    """Same chat keeps its session id; a different chat gets a fresh one."""
    client = RecordingClient(
        [
            [
                {
                    "update_id": i,
                    "message": {"chat": {"id": cid}, "from": {"id": 7}, "text": f"msg{i}"},
                }
                for i, cid in ((1, 42), (2, 43), (3, 42))
            ]
        ]
    )
    runner = TelegramBotRunner(
        client=client,
        chat_service=chat_service,
        audit=audit_log,
        allowed_chat_ids=frozenset({42, 43}),
    )

    sessions: dict[tuple[int, int], str] = {}
    for incoming in parse_updates(client.get_updates(0)):
        runner.route(incoming, sessions)

    assert set(sessions) == {(42, 7), (43, 7)}
    assert sum(1 for cid, _ in client.sent) == 3


def test_long_unicode_reply_splits_without_losing_text():
    from personal_agent.infrastructure.integrations.telegram.client import split_message

    text = "A long reply 😀\n" * 800
    chunks = split_message(text)
    assert len(chunks) > 1
    assert "".join(chunks) == text
    assert all(len(chunk.encode("utf-16-le")) // 2 <= 4096 for chunk in chunks)


def test_get_me_unwraps_bot_identity():
    client = _client(
        lambda request: httpx.Response(
            200, json={"ok": True, "result": {"id": 123, "username": "my_bot"}}
        )
    )
    assert client.get_me()["username"] == "my_bot"


def test_session_recovers_after_bot_restart(chat_service, audit_log):
    client = RecordingClient([])
    runner = TelegramBotRunner(
        client=client, chat_service=chat_service, audit=audit_log, allowed_chat_ids=frozenset({42})
    )
    incoming = parse_updates(
        [{"update_id": 1, "message": {"chat": {"id": 42}, "from": {"id": 7}, "text": "first"}}]
    )[0]
    first = {}
    runner.route(incoming, first)
    restarted = {}
    runner.route(incoming, restarted)
    assert first[(42, 7)] == restarted[(42, 7)]


def test_commands_do_not_call_model(chat_service, audit_log, scripted_provider):
    client = RecordingClient([])
    runner = TelegramBotRunner(
        client=client, chat_service=chat_service, audit=audit_log, allowed_chat_ids=frozenset({42})
    )
    for text in ["/start", "/help", "/new"]:
        incoming = parse_updates(
            [{"update_id": 1, "message": {"chat": {"id": 42}, "from": {"id": 7}, "text": text}}]
        )[0]
        runner.route(incoming, {})
    assert len(client.sent) == 3
    assert scripted_provider.calls == []


def test_poll_advances_past_unsupported_updates_and_survives_send_failure(
    chat_service, audit_log, session_factory
):
    class PollClient(RecordingClient):
        def __init__(self):
            super().__init__([])
            self.offsets = []
            self.attempts = 0

        def get_me(self):
            return {"username": "test_bot"}

        def get_updates(self, offset):
            self.offsets.append(offset)
            if len(self.offsets) > 1:
                raise KeyboardInterrupt()
            return [
                {"update_id": 1, "message": {"sticker": {}}},
                *[
                    {
                        "update_id": i,
                        "message": {"chat": {"id": 42}, "from": {"id": 7}, "text": "hi"},
                    }
                    for i in (2, 3)
                ],
                {"update_id": 4, "message": {"photo": []}},
            ]

        def send_message(self, chat_id, text):
            self.attempts += 1
            if self.attempts == 1:
                raise TelegramNetworkError("test failure")
            super().send_message(chat_id, text)

    client = PollClient()
    runner = TelegramBotRunner(
        client=client, chat_service=chat_service, audit=audit_log, allowed_chat_ids=frozenset({42})
    )
    with pytest.raises(KeyboardInterrupt):
        runner.run_forever()
    assert client.offsets == [0, 5]
    assert len(client.sent) == 1
    assert "telegram.reply_send_failed" in [r.event for r in recent_audit(session_factory)]


def test_private_owner_task_identity_is_shared_but_groups_are_isolated(tmp_path):
    from personal_agent.app.container import build_app
    from personal_agent.config.settings import Settings
    from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider

    provider = FakeProvider(
        [
            AssistantTurn(
                tool_calls=(
                    ToolCall(id="a", name="task_create", arguments={"title": "Private task"}),
                )
            ),
            AssistantTurn(content="Created."),
            AssistantTurn(tool_calls=(ToolCall(id="b", name="task_list", arguments={}),)),
            AssistantTurn(content="No group tasks."),
        ]
    )
    container = build_app(
        settings=Settings.from_env({"DATABASE_URL": f"sqlite:///{tmp_path / 'identity.db'}"}),
        provider=provider,
    )
    runner = TelegramBotRunner(
        client=RecordingClient([]),
        chat_service=container.chat,
        audit=container.audit,
        allowed_chat_ids=frozenset({42, -100}),
    )
    private = parse_updates(
        [
            {
                "update_id": 1,
                "message": {"chat": {"id": 42}, "from": {"id": 42}, "text": "Create a task"},
            }
        ]
    )[0]
    group = parse_updates(
        [
            {
                "update_id": 2,
                "message": {"chat": {"id": -100}, "from": {"id": 42}, "text": "List tasks"},
            }
        ]
    )[0]
    runner.route(private, {})
    assert container.tasks.list()[0].owner_user_id == "dashboard"
    runner.route(group, {})
    tool_message = next(m for m in provider.calls[-1][0] if m.role == "tool")
    assert tool_message.content == "[]"
