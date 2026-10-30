"""Telegram frontend — thin: builds the runner and blocks on `run_forever()`.

Polling lives in infrastructure/integrations/telegram; agent use cases live in application.
Run with: `personal-agent telegram`
"""

from __future__ import annotations

import logging
import sys

import typer

from personal_agent.app.container import build_app
from personal_agent.config.settings import load_settings
from personal_agent.domain.exceptions import ConfigurationError
from personal_agent.infrastructure.integrations.telegram.client import TelegramBotClient
from personal_agent.infrastructure.integrations.telegram.exceptions import TelegramAuthError
from personal_agent.infrastructure.integrations.telegram.runner import (
    TelegramBotRunner,
    build_allowed_chats,
)

logger = logging.getLogger(__name__)


def run() -> None:
    """Entry used by the CLI; exits non-zero on misconfiguration."""
    settings = load_settings()
    if not settings.telegram_bot_token:
        raise ConfigurationError(
            "TELEGRAM_BOT_TOKEN is not set. Create a bot with @BotFather and add the token to .env."
        )

    container = build_app(settings=settings)
    client = TelegramBotClient(bot_token=settings.telegram_bot_token)

    runner = TelegramBotRunner(
        client=client,
        chat_service=container.chat,
        audit=container.audit,
        allowed_chat_ids=build_allowed_chats(settings.telegram_allowed_chat_ids),
    )
    try:
        runner.run_forever()  # blocks; Ctrl-C is the clean exit
    except TelegramAuthError:
        typer.secho("Bot token rejected by Telegram.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from None
    except KeyboardInterrupt:
        logger.info("Telegram bot stopped by user.")
    except Exception as exc:  # noqa: BLE001 — surface a final human-readable line
        typer.secho(f"Telegram bot crashed: {exc}", fg=typer.colors.RED, err=True)
        logger.exception("Telegram bot crashed unexpectedly.")
        sys.exit(1)
