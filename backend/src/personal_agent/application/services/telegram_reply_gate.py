"""Decide whether an inbound Telegram message needs an agent reply.

Fail-open callers should treat exceptions as needs_reply=True.
"""

from __future__ import annotations

import re

# Casual acknowledgements / noise — stay silent.
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
        "👍",
        "👌",
        "🙏",
        "😂",
        "🙂",
        "😊",
    }
)

_REQUEST_HINTS = (
    "please",
    "can you",
    "could you",
    "would you",
    "will you",
    "help",
    "remind",
    "send",
    "email",
    "schedule",
    "create",
    "update",
    "delete",
    "check",
    "find",
    "what",
    "when",
    "where",
    "why",
    "how",
    "who",
    "need",
    "want",
    "tell me",
    "show me",
    "list",
    "summarize",
    "reply",
    "answer",
)


def needs_reply(text: str) -> bool:
    """Return True when the message looks like a question, request, or action."""
    raw = (text or "").strip()
    if not raw:
        return False
    lowered = raw.lower().strip()
    # Strip surrounding punctuation for exact casual matches.
    normalized = re.sub(r"^[^\w]+|[^\w]+$", "", lowered, flags=re.UNICODE)
    if normalized in _SILENT_EXACT or lowered in _SILENT_EXACT:
        return False
    # Single emoji / very short reaction without letters
    if len(raw) <= 4 and not re.search(r"[a-zA-Z0-9]", raw):
        return False
    if "?" in raw:
        return True
    for hint in _REQUEST_HINTS:
        if hint in lowered:
            return True
    # Longer substantive messages still get a reply
    return len(raw.split()) >= 6
