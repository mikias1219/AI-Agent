"""Decide whether an inbound Telegram message needs an agent reply.

Language-independent (INT-TG-02): silence only for acknowledgements and emoji.
Fail-open callers should treat exceptions as needs_reply=True.
"""

from __future__ import annotations

import re
import unicodedata

# Multilingual acknowledgements / noise — stay silent (not English request hints).
_SILENT_EXACT = frozenset(
    {
        "ok",
        "okay",
        "k",
        "kk",
        "thanks",
        "thank you",
        "thx",
        "ty",
        "np",
        "cool",
        "nice",
        "lol",
        "lmao",
        "haha",
        "hehe",
        "yes",
        "yep",
        "yeah",
        "yup",
        "no",
        "nope",
        "hi",
        "hello",
        "hey",
        "gm",
        "gn",
        # French
        "merci",
        "ok merci",
        "d'accord",
        "daccord",
        "oui",
        "non",
        "salut",
        # Spanish
        "gracias",
        "ok gracias",
        "sí",
        "si",
        "vale",
        "hola",
        # Arabic (common short forms)
        "شكرا",
        "شكراً",
        "تمام",
        "حسنا",
        "حسناً",
        "اهلا",
        "أهلا",
        "مرحبا",
    }
)

_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002700-\U000027bf"
    "\U0001f1e0-\U0001f1ff"
    "\U00002600-\U000026ff"
    "\U0000fe00-\U0000fe0f"
    "\U0000200d"
    "]+",
    flags=re.UNICODE,
)


def needs_reply(text: str) -> bool:
    """Return True unless the message is empty, emoji-only, or a short acknowledgement."""
    raw = (text or "").strip()
    if not raw:
        return False
    lowered = unicodedata.normalize("NFKC", raw).casefold().strip()
    normalized = re.sub(r"^[^\w]+|[^\w]+$", "", lowered, flags=re.UNICODE)
    if normalized in _SILENT_EXACT or lowered in _SILENT_EXACT:
        return False
    without_emoji = _EMOJI_RE.sub("", raw).strip()
    if not without_emoji:
        return False
    # Very short reaction without letters/numbers in any script → silent
    return not (len(raw) <= 4 and not re.search(r"\w", raw, flags=re.UNICODE))


def is_private_owner_chat(*, chat_id: int, sender_id: int) -> bool:
    """Owner DM: positive chat id equal to the sender (Telegram private chats)."""
    return chat_id > 0 and chat_id == sender_id


def message_mentions_bot(text: str, *, bot_username: str, entities: list[dict] | None) -> bool:
    """True when the message @-mentions this bot (entity or plain @username)."""
    username = (bot_username or "").lstrip("@").casefold()
    if not username:
        return False
    for entity in entities or []:
        if entity.get("type") != "mention":
            continue
        offset = int(entity.get("offset", 0))
        length = int(entity.get("length", 0))
        fragment = text[offset : offset + length]
        if fragment.lstrip("@").casefold() == username:
            return True
    needle = f"@{username}"
    return needle in text.casefold()
