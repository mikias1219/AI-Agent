"""Read-only Telegram identity verification; never sends a message."""

from typing import Protocol

from personal_agent.domain.exceptions import ConfigurationError


class BotIdentityClient(Protocol):
    def get_me(self) -> dict: ...


class TelegramService:
    def __init__(self, client: BotIdentityClient | None) -> None:
        self._client = client

    def verify(self) -> dict:
        if self._client is None:
            raise ConfigurationError("Add TELEGRAM_BOT_TOKEN to backend/.env first.")
        bot = self._client.get_me()
        return {"id": bot.get("id"), "username": bot.get("username"), "name": bot.get("first_name")}
