"""Chat use case shared by CLI, Telegram, and the authenticated web API.

One `turn()` = load session → inject memory → run the agent (which may call tools
through the enforcement gate) → persist every message → return the final text.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from personal_agent.application.agent import Agent
from personal_agent.domain.conversation import build_system_context, omit_retired_tool_messages
from personal_agent.domain.models import Message, RunOutcome, ToolContext
from personal_agent.domain.ports import AuditLog, ConversationRepository, MemoryStore

logger = logging.getLogger(__name__)


class ChatService:
    """Turn-oriented chat orchestration, interface-agnostic."""

    def __init__(
        self,
        *,
        agent: Agent,
        conversations: ConversationRepository,
        memory: MemoryStore,
        audit: AuditLog | None = None,
        history_limit: int = 20,
    ) -> None:
        self._agent = agent
        self._conversations = conversations
        self._memory = memory
        self._audit = audit
        self._history_limit = history_limit

    def latest_session(self, user_id: str) -> str | None:
        return self._conversations.latest_session(user_id)

    def start_session(self, user_id: str, origin: str) -> str:
        session_id = self._conversations.create_session(user_id)
        self._record(
            "conversation.session_created", user_id, {"session_id": session_id, "origin": origin}
        )
        return session_id

    def turn(
        self,
        *,
        user_id: str = "default",
        session_id: str | None = None,
        text: str,
        origin: str = "cli",
        identity_user_id: str | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> tuple[str, str]:
        """Run one chat turn; returns (session_id, assistant_text).

        A new session id is created when `session_id` is None, so callers can
        resume conversations across CLI/API/Telegram without knowing storage.
        """
        text = text.strip()
        if not text:
            session_id = session_id or self._conversations.create_session(user_id)
            return session_id, ""

        if session_id is None:
            session_id = self._conversations.create_session(user_id)
            self._record(
                "conversation.session_created",
                user_id,
                {"session_id": session_id, "origin": origin},
            )
        identity = identity_user_id or user_id
        ctx = ToolContext(user_id=identity, session_id=session_id, origin=origin)

        self._conversations.append(session_id, Message(role="user", content=text))
        self._record(
            "chat.user_message",
            user_id,
            {"session_id": session_id, "origin": origin, "character_count": len(text)},
        )
        history = self._conversations.load(session_id, limit=self._history_limit)
        history = omit_retired_tool_messages(history, {"noop"})
        system_context = build_system_context(identity, self._memory)
        if system_context is not None:
            history = [system_context, *history]

        try:
            outcome = self._agent.run_turn(history, ctx, on_token=on_token)
        except Exception as exc:
            self._record(
                "chat.turn_failed",
                user_id,
                {
                    "session_id": session_id,
                    "origin": origin,
                    "error_type": type(exc).__name__,
                },
            )
            raise
        for message in outcome.new_messages:
            self._conversations.append(session_id, message)
        reply = outcome_from_agent(outcome)
        self._record(
            "chat.assistant_response",
            user_id,
            {
                "session_id": session_id,
                "origin": origin,
                "character_count": len(reply),
                "tool_call_count": len(outcome.tool_calls_made),
            },
        )
        return session_id, reply

    def _record(self, event: str, actor: str, details: dict[str, object]) -> None:
        if self._audit is not None:
            self._audit.record(event, actor, details)


def outcome_from_agent(outcome: RunOutcome) -> str:
    """Fall back to a friendly message when the model returned nothing usable."""
    if not outcome.final_text:
        logger.warning(
            "Agent turn produced empty text; %d tool calls.", len(outcome.tool_calls_made)
        )
        return "(The model returned no final text.)"
    return outcome.final_text
