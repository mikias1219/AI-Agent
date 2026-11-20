"""Telegram identity verification and owner-initiated test sends."""

from typing import Protocol

from personal_agent.domain.exceptions import ConfigurationError


class BotIdentityClient(Protocol):
    def get_me(self) -> dict: ...


class BotMessageClient(Protocol):
    def get_me(self) -> dict: ...

    def send_message(self, chat_id: int, text: str, *, reply_markup: dict | None = None) -> None: ...


class TelegramService:
    def __init__(self, client: BotMessageClient | None) -> None:
        self._client = client

    def verify(self) -> dict:
        if self._client is None:
            raise ConfigurationError("Add TELEGRAM_BOT_TOKEN to backend/.env first.")
        bot = self._client.get_me()
        return {"id": bot.get("id"), "username": bot.get("username"), "name": bot.get("first_name")}

    def send_message(self, chat_id: int, text: str) -> None:
        if self._client is None:
            raise ConfigurationError("Add TELEGRAM_BOT_TOKEN to backend/.env first.")
        self._client.send_message(chat_id, text)
