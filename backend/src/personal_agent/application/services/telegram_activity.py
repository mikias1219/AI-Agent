"""Shared Telegram audit activity query (dashboard API and agent tools)."""

from __future__ import annotations

from typing import Any

from personal_agent.domain.ports import AuditReader

TELEGRAM_ACTIVITY_EVENTS: tuple[str, ...] = (
    "telegram.reply_sent",
    "telegram.reply_send_failed",
    "telegram.ignored_no_reply",
    "security.telegram_unauthorized_chat",
    "telegram.identity_verified",
)


def list_telegram_audit_activity(audit: AuditReader, *, limit: int = 50) -> list[dict[str, Any]]:
    return audit.list_recent(limit=limit, events=list(TELEGRAM_ACTIVITY_EVENTS))
