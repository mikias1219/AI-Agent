"""Inline approval callbacks: owner-only, spoofed ignored, duplicates safe."""

from __future__ import annotations

from dataclasses import dataclass

from personal_agent.domain.approvals import Approval, ApprovalStatus
from personal_agent.infrastructure.integrations.telegram.mapper import (
    TelegramCallback,
    parse_approval_callback,
    parse_callback,
)
from personal_agent.infrastructure.integrations.telegram.runner import TelegramBotRunner


def test_parse_approval_callback():
    assert parse_approval_callback("apr:abc123:approve") == ("abc123", True)
    assert parse_approval_callback("apr:abc123:deny") == ("abc123", False)
    assert parse_approval_callback("apr:abc:maybe") is None
    assert parse_approval_callback("nope") is None


def test_parse_callback_update():
    raw = {
        "update_id": 9,
        "callback_query": {
            "id": "cb1",
            "data": "apr:aid1:approve",
            "from": {"id": 42, "username": "owner"},
            "message": {"chat": {"id": 42, "type": "private"}},
        },
    }
    cb = parse_callback(raw)
    assert cb is not None
    assert cb.chat_id == 42 and cb.sender_id == 42 and cb.data.endswith("approve")


@dataclass
class _Outcome:
    approval: Approval
    executed: bool = False


class _FakeApprovals:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []
        self.approval = Approval(
            id="aid1",
            tool_name="google_gmail_send",
            arguments={},
            arguments_hash="h",
            user_id="dashboard",
            session_id="s1",
            origin="telegram",
            summary="Send email",
            status=ApprovalStatus.PENDING,
        )

    def decide(self, approval_id: str, approve: bool, *, actor: str, channel: str):
        self.calls.append((approval_id, approve))
        if len(self.calls) > 1:
            self.approval.status = ApprovalStatus.APPROVED
            return _Outcome(self.approval, executed=False)
        self.approval.status = ApprovalStatus.APPROVED
        return _Outcome(self.approval, executed=True)

    def list_approvals(self, status=None, limit=50):
        return [self.approval]


class _FakeClient:
    def __init__(self) -> None:
        self.answered: list[tuple[str, str]] = []
        self.sent: list[tuple[int, str]] = []

    def answer_callback_query(self, callback_id: str, *, text: str = "") -> None:
        self.answered.append((callback_id, text))

    def send_message(self, chat_id: int, text: str, *, reply_markup=None) -> None:
        self.sent.append((chat_id, text))


class _FakeChat:
    pass


class _FakeAudit:
    def __init__(self) -> None:
        self.events: list[str] = []

    def record(self, event: str, actor: str, details: dict) -> None:
        self.events.append(event)


def _runner(approvals, client, allowed=frozenset({42})):
    return TelegramBotRunner(
        client=client,
        chat_service=_FakeChat(),  # type: ignore[arg-type]
        audit=_FakeAudit(),  # type: ignore[arg-type]
        allowed_chat_ids=allowed,
        approval_service=approvals,
        bot_label="aura",
    )


def test_spoofed_group_callback_ignored():
    approvals = _FakeApprovals()
    client = _FakeClient()
    runner = _runner(approvals, client)
    callback = TelegramCallback(
        update_id=1,
        callback_id="cb",
        chat_id=-100,
        sender_id=42,
        data="apr:aid1:approve",
        chat_type="supergroup",
    )
    # Group chat id not equal sender → spoof path (also not in allowlist typically)
    runner = _runner(approvals, client, allowed=frozenset({-100, 42}))
    runner.route_callback(callback)
    assert approvals.calls == []
    assert client.answered and "private" in client.answered[0][1].lower()


def test_owner_callback_approves_once_on_duplicate():
    approvals = _FakeApprovals()
    client = _FakeClient()
    runner = _runner(approvals, client)
    callback = TelegramCallback(
        update_id=1,
        callback_id="cb1",
        chat_id=42,
        sender_id=42,
        data="apr:aid1:approve",
        chat_type="private",
    )
    runner.route_callback(callback)
    runner.route_callback(
        TelegramCallback(
            update_id=2,
            callback_id="cb2",
            chat_id=42,
            sender_id=42,
            data="apr:aid1:approve",
            chat_type="private",
        )
    )
    assert len(approvals.calls) == 2
    assert client.answered[1][1].lower().startswith("already")
