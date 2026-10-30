"""Telegram-specific failures, translated to the core error hierarchy at this boundary."""

from __future__ import annotations

from personal_agent.domain.exceptions import AgentError


class TelegramError(AgentError):
    """Base for this integration's failures; callers catch AgentError already."""


class TelegramAuthError(TelegramError):
    """The bot token was rejected by Telegram."""

    def __init__(self) -> None:
        super().__init__("Telegram rejected the bot token (401). Check TELEGRAM_BOT_TOKEN.")


class TelegramNetworkError(TelegramError):
    """Transient transport trouble: timeouts, DNS, connection resets."""
