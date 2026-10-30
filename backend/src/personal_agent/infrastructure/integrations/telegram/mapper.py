"""Telegram payloads <-> clean value objects (no transport, no business logic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TelegramIncoming:
    """One user-visible incoming message; ids are Telegram's numeric ids as strings."""

    update_id: int
    chat_id: int
    sender_id: int
    username: str | None
    text: str

    @property
    def sender_key(self) -> str:
        """Stable identity string used for memory/repos (never a phone number)."""
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
    return TelegramIncoming(
        update_id=update_id,
        chat_id=chat_id,
        sender_id=sender_id,
        username=sender.get("username") or None,
        text=text.strip(),
    )


def parse_updates(raw_list: list[dict[str, Any]]) -> list[TelegramIncoming]:
    """Map a getUpdates batch, dropping non-chat content silently."""
    parsed = []
    for item in raw_list if isinstance(raw_list, list) else []:
        incoming = parse_update(item if isinstance(item, dict) else {})
        if incoming is not None:
            parsed.append(incoming)
    return parsed
