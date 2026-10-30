"""Inbound Telegram loop: poll → owner gate → ChatService.turn → send reply.

Security at this boundary (fail-closed):
- Only chats in `TELEGRAM_ALLOWED_CHAT_IDS` are answered; anything else is
  ignored (no confirmation sent) and audit-logged.
- The bot token is never logged; only the bot's username is.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from contextlib import contextmanager

from personal_agent.application.services.chat_service import ChatService
from personal_agent.domain.exceptions import AgentError
from personal_agent.domain.ports import AuditLog
from personal_agent.infrastructure.integrations.telegram.client import TelegramBotClient
from personal_agent.infrastructure.integrations.telegram.mapper import (
    TelegramIncoming,
    parse_update,
)

logger = logging.getLogger(__name__)

ERROR_REPLY = "Sorry, something went wrong on my side. Try again shortly."
ERROR_BACKOFF_SECONDS = 10.0
EMPTY_TICK_SECONDS = 1.0


class TelegramBotRunner:
    """One long-polling session; runs until `run_forever` is interrupted."""

    def __init__(
        self,
        *,
        client: TelegramBotClient,
        chat_service: ChatService,
        audit: AuditLog,
        allowed_chat_ids: frozenset[int],
        bot_label: str = "personal-agent",
    ) -> None:
        self._client = client
        self._chat_service = chat_service
        self._audit = audit
        self._allowed = allowed_chat_ids
        self._bot_label = bot_label

    def run_forever(self, stop_event: threading.Event | None = None) -> None:
        """Start polling; KeyboardInterrupt (Ctrl-C) is the only clean exit."""
        stop = stop_event or threading.Event()
        sessions: dict[tuple[int, int], str] = {}
        offset = 0
        try:
            self._runtime("starting")
            me = self._client.get_me()
            self._bot_label = me.get("username", self._bot_label)
            self._runtime("polling")
            while not stop.is_set():
                try:
                    updates = self._client.get_updates(offset)
                    self._runtime("polling")
                except AgentError as exc:
                    self._runtime("error", type(exc).__name__)
                    logger.warning("Telegram poll failed: %s", type(exc).__name__)
                    stop.wait(ERROR_BACKOFF_SECONDS)
                    continue
                for raw in updates:
                    if stop.is_set():
                        break
                    # Confirm all valid update IDs, including unsupported content.
                    if isinstance(raw, dict) and isinstance(raw.get("update_id"), int):
                        offset = max(offset, raw["update_id"] + 1)
                    incoming = parse_update(raw)
                    if incoming is None:
                        continue
                    try:
                        self._runtime("responding")
                        self.route(incoming, sessions)
                    except AgentError as exc:
                        # A failed send must not kill polling or resend the entire turn.
                        logger.warning("Telegram reply failed: %s", type(exc).__name__)
                        self._runtime("error", type(exc).__name__)
                    else:
                        self._runtime("polling")
                if not updates:
                    stop.wait(EMPTY_TICK_SECONDS)
        finally:
            self._runtime("stopped")

    def _runtime(self, phase: str, error_type: str = "") -> None:
        self._audit.record(
            "telegram.runtime",
            "telegram",
            {"phase": phase, "username": self._bot_label, "error_type": error_type},
        )

    @contextmanager
    def _typing(self, chat_id: int):
        stopped = threading.Event()

        def indicate():
            while not stopped.is_set():
                try:
                    self._client.send_typing(chat_id)
                except AgentError:
                    logger.debug("Telegram typing indicator unavailable.")
                if stopped.wait(4):
                    break

        threading.Thread(target=indicate, daemon=True, name="telegram-typing").start()
        try:
            yield
        finally:
            stopped.set()

    def route(self, incoming: TelegramIncoming, sessions: dict[tuple[int, int], str]) -> None:
        """Owner gate first, then one chat turn, then a direct reply to the chat."""
        if incoming.chat_id not in self._allowed:
            self._audit.record(
                "security.telegram_unauthorized_chat",
                incoming.sender_key,
                {"chat_id": str(incoming.chat_id), "bot": self._bot_label},
            )
            logger.warning("Ignored message from unauthorized chat %s.", incoming.chat_id)
            return

        command = incoming.text.split()[0].split("@")[0].lower()
        user_id = f"telegram:{incoming.chat_id}:{incoming.sender_id}"
        if command in {"/start", "/help", "/new"}:
            if command == "/new":
                sessions[(incoming.chat_id, incoming.sender_id)] = self._chat_service.start_session(
                    user_id, "telegram"
                )
                reply = "Started a fresh conversation. What would you like help with?"
            else:
                reply = (
                    "Hi! I’m your personal agent. Ask a question or tell me what you need. "
                    "I’ll reply here. Use /new for a fresh conversation and /help for help."
                )
            self._send_reply(
                incoming.chat_id,
                incoming.sender_key,
                sessions.get((incoming.chat_id, incoming.sender_id), ""),
                reply,
            )
            return
        # One conversation per sender/chat; numeric identity survives username changes.
        session_key = (incoming.chat_id, incoming.sender_id)
        session_id = sessions.get(session_key) or self._chat_service.latest_session(user_id)
        try:
            with self._typing(incoming.chat_id):
                session_id, reply = self._chat_service.turn(
                    user_id=user_id,
                    session_id=session_id,
                    text=incoming.text,
                    origin="telegram",
                    # Private allowlisted chats act for the single workspace owner. Groups
                    # retain sender isolation; their context cannot list the owner's tasks.
                    identity_user_id=(
                        "dashboard"
                        if incoming.chat_id == incoming.sender_id and incoming.chat_id > 0
                        else None
                    ),
                )
        except AgentError as exc:
            logger.exception("Chat turn failed for chat %s: %s", incoming.chat_id, exc)
            self._send_reply(
                incoming.chat_id,
                incoming.sender_key,
                session_id or "",
                ERROR_REPLY,
                failed_turn=True,
            )
            return
        sessions[session_key] = session_id
        self._send_reply(
            incoming.chat_id,
            incoming.sender_key,
            session_id,
            reply or "(no content)",
        )

    def _send_reply(
        self,
        chat_id: int,
        actor: str,
        session_id: str,
        text: str,
        *,
        failed_turn: bool = False,
    ) -> None:
        details = {
            "chat_id": str(chat_id),
            "session_id": session_id,
            "character_count": len(text),
            "failed_turn": failed_turn,
        }
        try:
            self._client.send_message(chat_id, text)
        except AgentError as exc:
            self._audit.record(
                "telegram.reply_send_failed",
                actor,
                {**details, "error_type": type(exc).__name__},
            )
            raise
        self._audit.record("telegram.reply_sent", actor, details)


def build_allowed_chats(raw: str | Mapping[int, str] | None) -> frozenset[int]:
    """Parse `TELEGRAM_ALLOWED_CHAT_IDS` ('123,-456') into a frozenset; skip junk."""
    if raw is None:
        return frozenset()
    if isinstance(raw, Mapping):
        return frozenset(int(value) for value in raw)
    allowed: set[int] = set()
    for piece in raw.replace(";", ",").split(","):
        piece = piece.strip()
        if piece.lstrip("-").isdigit():
            allowed.add(int(piece))
        elif piece:
            logger.warning("Ignoring non-numeric chat id in allowlist: %r", piece)
    return frozenset(allowed)
