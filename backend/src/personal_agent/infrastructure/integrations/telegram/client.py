"""HTTP client for the Telegram Bot API (long polling, sync `httpx`).

Never logs the token: it is embedded only in the request path and redacted by
`config.logging.RedactionFilter` as a backstop. Tests inject an `httpx.Client`
(see `tests/integration/test_telegram_runner.py`) so no network is needed.
"""

from __future__ import annotations

import logging

import httpx

from personal_agent.infrastructure.integrations.telegram.exceptions import (
    TelegramAuthError,
    TelegramError,
    TelegramNetworkError,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.telegram.org"
POLL_TIMEOUT_SECONDS = 25
POLL_EXTRA_GRACE_SECONDS = 15  # poll timeout + this = httpx request timeout


class TelegramBotClient:
    """Telegram Bot API transport: `getUpdates`, `sendMessage`, `getMe`."""

    def __init__(self, bot_token: str, http: httpx.Client | None = None) -> None:
        if not bot_token.strip():
            raise TelegramError("TELEGRAM_BOT_TOKEN is empty; cannot start Telegram bot.")
        self._token = bot_token.strip()
        self._http = http or httpx.Client(
            base_url=BASE_URL, timeout=POLL_TIMEOUT_SECONDS + POLL_EXTRA_GRACE_SECONDS
        )

    def get_me(self) -> dict:
        """Identity check used at startup to verify the token works."""
        return self._call("getMe").get("result", {})

    def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        reply_markup: dict | None = None,
    ) -> None:
        """Send plain text (no parse_mode, so user-provided text can't break markup)."""
        chunks = split_message(text)
        for index, chunk in enumerate(chunks):
            payload: dict = {
                "chat_id": chat_id,
                "text": chunk,
                "link_preview_options": {"is_disabled": True},
            }
            # Attach keyboard only on the last chunk so buttons stay with the prompt.
            if reply_markup is not None and index == len(chunks) - 1:
                payload["reply_markup"] = reply_markup
            self._call("sendMessage", payload)

    def answer_callback_query(self, callback_id: str, *, text: str = "") -> None:
        payload: dict = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text[:200]
        self._call("answerCallbackQuery", payload)

    def send_typing(self, chat_id: int) -> None:
        self._call("sendChatAction", {"chat_id": chat_id, "action": "typing"})

    def get_updates(self, offset: int) -> list[dict]:
        """Long-poll updates newer than `offset`; returns raw payload dicts."""
        data = self._call(
            "getUpdates",
            {
                "offset": offset,
                "timeout": POLL_TIMEOUT_SECONDS,
                "allowed_updates": ["message", "callback_query"],
            },
        )
        return data.get("result", []) if isinstance(data, dict) else []

    def _call(self, method: str, payload: dict | None = None) -> dict:
        try:
            response = self._http.post(
                f"/bot{self._token}/{method}",
                json=payload or {},
                timeout=40 if method == "getUpdates" else 10,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                raise TelegramAuthError() from exc
            raise TelegramError(f"Telegram '{method}' failed with HTTP {status}.") from exc
        except httpx.HTTPError as exc:
            raise TelegramNetworkError(
                "Telegram could not be reached. Check your connection."
            ) from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise TelegramError("Telegram returned non-JSON content.") from exc
        if not isinstance(data, dict) or not data.get("ok", False):
            description = data.get("description") if isinstance(data, dict) else "?"
            raise TelegramError(f"Telegram 'ok: false' ({method}): {description}")
        return data


def approval_inline_keyboard(approval_id: str) -> dict:
    """Inline Approve / Deny keyboard (INT-TG-03)."""
    return {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"apr:{approval_id}:approve"},
                {"text": "Deny", "callback_data": f"apr:{approval_id}:deny"},
            ]
        ]
    }


def split_message(text: str, limit: int = 4096) -> list[str]:
    """Bound UTF-16 length, preserving every character, including astral emoji."""
    chunks, current = [], []
    units = 0
    for character in text:
        size = 2 if ord(character) > 0xFFFF else 1
        if current and units + size > limit:
            chunks.append("".join(current))
            current, units = [], 0
        current.append(character)
        units += size
    if current:
        chunks.append("".join(current))
    return chunks
