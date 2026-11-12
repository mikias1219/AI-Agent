"""Inbound Telegram loop: poll → owner gate → ChatService.turn → send reply.

Security at this boundary (fail-closed):
- Only chats in `TELEGRAM_ALLOWED_CHAT_IDS` are answered; anything else is
  ignored (no confirmation sent) and audit-logged.
- The bot token is never logged; only the bot's username is.
- Approvals via inline callbacks only from the owner private chat (BR-12).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

from personal_agent.application.services.chat_service import ChatService
from personal_agent.application.services.telegram_reply_gate import (
    is_private_owner_chat,
    message_mentions_bot,
    needs_reply,
)
from personal_agent.domain.approvals import ApprovalStatus
from personal_agent.domain.exceptions import AgentError
from personal_agent.domain.ports import AuditLog
from personal_agent.infrastructure.integrations.telegram.client import (
    TelegramBotClient,
    approval_inline_keyboard,
)
from personal_agent.infrastructure.integrations.telegram.mapper import (
    TelegramCallback,
    TelegramIncoming,
    parse_approval_callback,
    parse_callback,
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
        approval_service: Any | None = None,
    ) -> None:
        self._client = client
        self._chat_service = chat_service
        self._audit = audit
        self._allowed = allowed_chat_ids
        self._bot_label = bot_label
        self._approvals = approval_service

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
                    if isinstance(raw, dict) and isinstance(raw.get("update_id"), int):
                        offset = max(offset, raw["update_id"] + 1)
                    callback = parse_callback(raw if isinstance(raw, dict) else {})
                    if callback is not None:
                        try:
                            self._runtime("responding")
                            self.route_callback(callback)
                        except AgentError as exc:
                            logger.warning("Telegram callback failed: %s", type(exc).__name__)
                            self._runtime("error", type(exc).__name__)
                        else:
                            self._runtime("polling")
                        continue
                    incoming = parse_update(raw if isinstance(raw, dict) else {})
                    if incoming is None:
                        continue
                    try:
                        self._runtime("responding")
                        self.route(incoming, sessions)
                    except AgentError as exc:
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

    def route_callback(self, callback: TelegramCallback) -> None:
        """Handle Approve/Deny inline buttons — owner private chat only (BR-12)."""
        parsed = parse_approval_callback(callback.data)
        if parsed is None:
            self._client.answer_callback_query(callback.callback_id, text="Unknown action.")
            return
        approval_id, approve = parsed
        if callback.chat_id not in self._allowed:
            self._audit.record(
                "security.telegram_unauthorized_callback",
                callback.sender_key,
                {"chat_id": str(callback.chat_id)},
            )
            self._client.answer_callback_query(callback.callback_id, text="Not allowed.")
            return
        if not is_private_owner_chat(chat_id=callback.chat_id, sender_id=callback.sender_id):
            self._audit.record(
                "security.telegram_spoofed_callback",
                callback.sender_key,
                {"chat_id": str(callback.chat_id), "approval_id": approval_id},
            )
            self._client.answer_callback_query(
                callback.callback_id, text="Approvals only in your private chat."
            )
            return
        if self._approvals is None:
            self._client.answer_callback_query(callback.callback_id, text="Approvals unavailable.")
            return
        try:
            outcome = self._approvals.decide(
                approval_id,
                approve,
                actor=callback.sender_key,
                channel="telegram_private",
            )
        except Exception as exc:  # noqa: BLE001 — answer the callback either way
            logger.warning("Approval decide failed: %s", type(exc).__name__)
            self._audit.record(
                "telegram.approval_callback_failed",
                callback.sender_key,
                {"approval_id": approval_id, "error_type": type(exc).__name__},
            )
            self._client.answer_callback_query(callback.callback_id, text=str(exc)[:180])
            return
        status = outcome.approval.status.value
        label = "Approved" if approve else "Denied"
        if outcome.approval.status is not ApprovalStatus.PENDING and not outcome.executed:
            # Duplicate callback: already decided.
            label = f"Already {status}"
        self._client.answer_callback_query(callback.callback_id, text=label)
        self._audit.record(
            "telegram.approval_callback",
            callback.sender_key,
            {
                "approval_id": approval_id,
                "decision": "approve" if approve else "deny",
                "status": status,
                "executed": outcome.executed,
            },
        )
        self._client.send_message(
            callback.chat_id,
            f"{label}: {outcome.approval.summary or outcome.approval.tool_name}",
        )

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

        owner_dm = is_private_owner_chat(chat_id=incoming.chat_id, sender_id=incoming.sender_id)
        if incoming.is_group and not message_mentions_bot(
            incoming.text,
            bot_username=self._bot_label,
            entities=list(incoming.entities),
        ):
            self._audit.record(
                "telegram.ignored_group_no_mention",
                incoming.sender_key,
                {"chat_id": str(incoming.chat_id)},
            )
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

        if not incoming.is_group:
            try:
                should_reply = needs_reply(incoming.text)
            except Exception:  # noqa: BLE001 — never drop a real ask because of the gate
                logger.exception("Telegram reply gate failed; answering anyway.")
                should_reply = True
            if not should_reply:
                self._audit.record(
                    "telegram.ignored_no_reply",
                    incoming.sender_key,
                    {"chat_id": str(incoming.chat_id), "preview": incoming.text[:80]},
                )
                return
        # Groups that mentioned the bot always get a reply.

        session_key = (incoming.chat_id, incoming.sender_id)
        session_id = sessions.get(session_key) or self._chat_service.latest_session(user_id)
        try:
            with self._typing(incoming.chat_id):
                session_id, reply = self._chat_service.turn(
                    user_id=user_id,
                    session_id=session_id,
                    text=incoming.text,
                    origin="telegram",
                    # True owner DMs (chat_id == sender_id) act as the workspace owner.
                    # Groups retain sender isolation; their context cannot list owner tasks.
                    identity_user_id="dashboard" if owner_dm else None,
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
        markup = None
        if owner_dm and self._approvals is not None:
            markup = self._pending_approval_markup(session_id)
        self._send_reply(
            incoming.chat_id,
            incoming.sender_key,
            session_id,
            reply or "(no content)",
            reply_markup=markup,
        )

    def _pending_approval_markup(self, session_id: str) -> dict | None:
        try:
            pending = self._approvals.list_approvals(ApprovalStatus.PENDING, limit=10)
        except Exception:  # noqa: BLE001
            return None
        for approval in pending:
            if approval.session_id == session_id and approval.origin == "telegram":
                return approval_inline_keyboard(approval.id)
        return None

    def _send_reply(
        self,
        chat_id: int,
        actor: str,
        session_id: str,
        text: str,
        *,
        failed_turn: bool = False,
        reply_markup: dict | None = None,
    ) -> None:
        details = {
            "chat_id": str(chat_id),
            "session_id": session_id,
            "character_count": len(text),
            "failed_turn": failed_turn,
            "has_keyboard": reply_markup is not None,
        }
        try:
            self._client.send_message(chat_id, text, reply_markup=reply_markup)
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
