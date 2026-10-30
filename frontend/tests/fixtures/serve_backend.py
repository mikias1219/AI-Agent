"""Isolated browser-test backend: temporary data, fake model, mocked Telegram HTTP."""

import tempfile
from pathlib import Path

import httpx
import uvicorn

from personal_agent.app.container import build_app
from personal_agent.application.services.telegram_service import TelegramService
from personal_agent.config.settings import Settings
from personal_agent.infrastructure.integrations.telegram.client import TelegramBotClient
from personal_agent.infrastructure.integrations.telegram.runner import TelegramBotRunner
from personal_agent.infrastructure.integrations.telegram.worker import TelegramWorker
from personal_agent.presentation.web.app import create_dashboard_app

with tempfile.TemporaryDirectory(prefix="agent-browser-") as directory:
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{Path(directory) / 'test.db'}",
            "DASHBOARD_SECRET_KEY": "browser-test-signing-key-not-for-production",
            "TELEGRAM_BOT_TOKEN": "123:test-only",
            "TELEGRAM_ALLOWED_CHAT_IDS": "42",
        }
    )
    container = build_app(settings=settings)
    delivered = []
    updates = [
        {
            "update_id": 1,
            "message": {
                "chat": {"id": 42},
                "from": {"id": 7},
                "text": "Hello from Telegram browser fixture",
            },
        }
    ]

    def telegram(request):
        if request.url.path.endswith("/getMe"):
            result = {"id": 123, "username": "fixture_bot", "first_name": "Fixture bot"}
        elif request.url.path.endswith("/getUpdates"):
            result = list(updates)
            updates.clear()
        else:
            delivered.append(request.content)
            result = {}
        return httpx.Response(200, json={"ok": True, "result": result})

    client = TelegramBotClient(
        "123:test-only",
        http=httpx.Client(
            base_url="https://api.telegram.org", transport=httpx.MockTransport(telegram)
        ),
    )
    container.telegram = TelegramService(client)
    container.telegram_worker = TelegramWorker(
        TelegramBotRunner(
            client=client,
            chat_service=container.chat,
            audit=container.audit,
            allowed_chat_ids=frozenset({42}),
        )
    )
    uvicorn.run(
        create_dashboard_app(container=container), host="127.0.0.1", port=8011, log_level="warning"
    )
