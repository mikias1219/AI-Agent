"""Telegram payloads <-> clean value objects (no transport, no business logic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class TelegramIncoming:
    """One user-visible incoming message; ids are Telegram's numeric ids as strings."""

    update_id: int
    chat_id: int
    sender_id: int
    username: str | None
    text: str
    chat_type: str = "private"
    entities: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    mentioned_usernames: tuple[str, ...] = field(default_factory=tuple)

    @property
    def sender_key(self) -> str:
        """Stable identity string used for memory/repos (never a phone number)."""
        return f"tg:{self.sender_id}"

    @property
    def is_group(self) -> bool:
        return self.chat_type in {"group", "supergroup"}


@dataclass(frozen=True, slots=True)
class TelegramCallback:
    """Inline keyboard callback from the owner (or anyone — runner must gate)."""

    update_id: int
    callback_id: str
    chat_id: int
    sender_id: int
    data: str
    chat_type: str = "private"

    @property
    def sender_key(self) -> str:
        return f"tg:{self.sender_id}"


def parse_update(raw: dict[str, Any]) -> TelegramIncoming | None:
    """Extract the first text message from one raw update, or None to skip it.

    Skips, without raising: edited messages, stickers/photos/voice, non-user
    content, and malformed shapes — the poller only wants chat text.
    """
    if not isinstance(raw, dict):
        return None
    message = raw.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    if not isinstance(chat, dict) or not isinstance(sender, dict):
        return None
    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        update_id, chat_id, sender_id = int(raw["update_id"]), int(chat["id"]), int(sender["id"])
    except (KeyError, TypeError, ValueError):
        return None
    entities_raw = message.get("entities") if isinstance(message.get("entities"), list) else []
    entities: list[dict[str, Any]] = [e for e in entities_raw if isinstance(e, dict)]
    mentions: list[str] = []
    for entity in entities:
        if entity.get("type") != "mention":
            continue
        try:
            offset = int(entity.get("offset", 0))
            length = int(entity.get("length", 0))
        except (TypeError, ValueError):
            continue
        fragment = text[offset : offset + length].lstrip("@")
        if fragment:
            mentions.append(fragment)
    return TelegramIncoming(
        update_id=update_id,
        chat_id=chat_id,
        sender_id=sender_id,
        username=sender.get("username") or None,
        text=text.strip(),
        chat_type=str(chat.get("type") or "private"),
        entities=tuple(entities),
        mentioned_usernames=tuple(mentions),
    )


def parse_callback(raw: dict[str, Any]) -> TelegramCallback | None:
    if not isinstance(raw, dict):
        return None
    cb = raw.get("callback_query")
    if not isinstance(cb, dict):
        return None
    message = cb.get("message") if isinstance(cb.get("message"), dict) else {}
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    sender = cb.get("from") if isinstance(cb.get("from"), dict) else {}
    data = cb.get("data")
    callback_id = cb.get("id")
    if not isinstance(data, str) or not data.strip():
        return None
    if not isinstance(callback_id, str) or not callback_id:
        return None
    try:
        update_id = int(raw["update_id"])
        chat_id = int(chat["id"])
        sender_id = int(sender["id"])
    except (KeyError, TypeError, ValueError):
        return None
    return TelegramCallback(
        update_id=update_id,
        callback_id=callback_id,
        chat_id=chat_id,
        sender_id=sender_id,
        data=data.strip(),
        chat_type=str(chat.get("type") or "private"),
    )


def parse_updates(raw_list: list[dict[str, Any]]) -> list[TelegramIncoming]:
    """Map a getUpdates batch, dropping non-chat content silently."""
    parsed = []
    for item in raw_list if isinstance(raw_list, list) else []:
        incoming = parse_update(item if isinstance(item, dict) else {})
        if incoming is not None:
            parsed.append(incoming)
    return parsed


def parse_approval_callback(data: str) -> tuple[str, bool] | None:
    """Parse `apr:{approval_id}:{approve|deny}` → (approval_id, approve)."""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "apr":
        return None
    approval_id, action = parts[1], parts[2]
    if not approval_id or action not in {"approve", "deny"}:
        return None
    return approval_id, action == "approve"
