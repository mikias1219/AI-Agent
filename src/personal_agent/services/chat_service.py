"""Chat use case — the API every interface (CLI, future REST/Telegram/web) calls.

One `turn()` = load session → inject memory → run the agent (which may call tools
through the enforcement gate) → persist every message → return the final text.
"""

from __future__ import annotations

import logging

from personal_agent.core.agent import Agent
from personal_agent.core.conversation import build_system_context
from personal_agent.core.ports import ConversationRepository, MemoryStore
from personal_agent.core.types import Message, RunOutcome, ToolContext

logger = logging.getLogger(__name__)


class ChatService:
    """Turn-oriented chat orchestration, interface-agnostic."""

    def __init__(
        self,
        *,
        agent: Agent,
        conversations: ConversationRepository,
        memory: MemoryStore,
        history_limit: int = 20,
    ) -> None:
        self._agent = agent
        self._conversations = conversations
        self._memory = memory
        self._history_limit = history_limit

    def turn(
        self,
        *,
        user_id: str = "default",
        session_id: str | None = None,
        text: str,
    ) -> tuple[str, str]:
        """Run one chat turn; returns (session_id, assistant_text).

        A new session id is created when `session_id` is None, so callers can
        resume conversations across CLI/API/Telegram without knowing storage.
        """
        text = text.strip()
        if not text:
            session_id = session_id or self._conversations.create_session(user_id)
            return session_id, ""

        session_id = session_id or self._conversations.create_session(user_id)
        ctx = ToolContext(user_id=user_id, session_id=session_id, origin="cli")

        self._conversations.append(session_id, Message(role="user", content=text))
        history = self._conversations.load(session_id, limit=self._history_limit)
        system_context = build_system_context(user_id, self._memory)
        if system_context is not None:
            history = [system_context, *history]

        outcome = self._agent.run_turn(history, ctx)
        return session_id, outcome_from_agent(outcome)


def outcome_from_agent(outcome: RunOutcome) -> str:
    """Fall back to a friendly message when the model returned nothing usable."""
    if not outcome.final_text:
        logger.warning(
            "Agent turn produced empty text; %d tool calls.", len(outcome.tool_calls_made)
        )
        return "(The model returned no final text.)"
    return outcome.final_text
