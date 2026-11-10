"""Telegram agent tools: read recent bot activity and send allowlisted messages."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from personal_agent.domain.models import ToolContext, ToolSpec
from personal_agent.infrastructure.integrations.telegram.client import TelegramBotClient

_EMPTY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

_ACTIVITY_CAP = 20


def telegram_tools(
    *,
    client: TelegramBotClient | None,
    allowed_chat_ids: frozenset[int],
    list_activity: Callable[[], list[dict]],
) -> list[ToolSpec]:
    def list_telegram_activity(_ctx: ToolContext, _args: Mapping[str, Any]) -> str:
        activity = list_activity()[:_ACTIVITY_CAP]
        return json.dumps(
            {
                "allowed_chat_ids": sorted(allowed_chat_ids),
                "activity": activity,
            }
        )

    def send_message(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        if client is None:
            raise ValueError("Telegram is not configured.")
        if not allowed_chat_ids:
            raise ValueError("Telegram allowlist is empty.")
        chat_id = int(args["chat_id"])
        text = str(args["text"])
        if chat_id not in allowed_chat_ids:
            raise ValueError("Chat is not allowlisted.")
        client.send_message(chat_id, text)
        return json.dumps({"chat_id": chat_id, "sent": True})

    chat_id_schema: dict[str, Any] = {"type": "integer"}
    if allowed_chat_ids:
        chat_id_schema = {
            "type": "integer",
            "enum": sorted(allowed_chat_ids),
        }

    return [
        ToolSpec(
            "telegram_list_activity",
            "List allowlisted Telegram chat IDs and recent Telegram-related audit activity.",
            _EMPTY_SCHEMA,
            "read",
            list_telegram_activity,
        ),
        ToolSpec(
            "telegram_send_message",
            "Send a text message to an allowlisted Telegram chat. Requires human approval.",
            {
                "type": "object",
                "properties": {
                    "chat_id": chat_id_schema,
                    "text": {"type": "string", "minLength": 1},
                },
                "required": ["chat_id", "text"],
                "additionalProperties": False,
            },
            "execute",
            send_message,
        ),
    ]
