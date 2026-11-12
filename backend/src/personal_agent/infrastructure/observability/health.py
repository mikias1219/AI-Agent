"""Extended health probes (OBS-05)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any


def probe_database(ping: Callable[[], None]) -> dict[str, Any]:
    try:
        ping()
        return {"ok": True, "error": None}
    except Exception as exc:  # noqa: BLE001 — health must never raise
        return {"ok": False, "error": type(exc).__name__}


def probe_provider(
    *,
    provider: str,
    ollama_reachable: bool,
    openai_key_present: bool,
) -> dict[str, Any]:
    if provider == "fake":
        return {"ok": True, "mode": "fake", "reachable": True}
    if provider == "ollama":
        return {"ok": ollama_reachable, "mode": "ollama", "reachable": ollama_reachable}
    if provider == "openai":
        return {
            "ok": openai_key_present,
            "mode": "openai",
            "reachable": openai_key_present,
        }
    if provider == "hermes":
        return {"ok": True, "mode": "hermes", "reachable": True}
    return {"ok": False, "mode": provider, "reachable": False}


def last_audit_at(audit_list: Callable[..., list[dict[str, Any]]], event: str) -> str | None:
    rows = audit_list(limit=1, offset=0, events=[event])
    if not rows:
        return None
    return str(rows[0].get("occurred_at") or "") or None


def build_health_payload(
    *,
    base: dict[str, Any],
    database_ping: Callable[[], None],
    audit_list: Callable[..., list[dict[str, Any]]],
    provider: str,
    ollama_reachable: bool,
    openai_key_present: bool,
    telegram_worker_running: bool,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    now = (clock or (lambda: datetime.now(UTC)))()
    database = probe_database(database_ping)
    provider_probe = probe_provider(
        provider=provider,
        ollama_reachable=ollama_reachable,
        openai_key_present=openai_key_present,
    )
    last_tick = last_audit_at(audit_list, "scheduler.tick")
    last_telegram = last_audit_at(audit_list, "telegram.message_handled")
    if last_telegram is None:
        last_telegram = last_audit_at(audit_list, "telegram.skipped")
    worker = {
        "telegram_running": telegram_worker_running,
        "last_heartbeat_at": last_telegram,
        "ok": True,
    }
    status = "ok" if database["ok"] and provider_probe["ok"] else "degraded"
    return {
        **base,
        "status": status,
        "checked_at": now.isoformat(),
        "database": database,
        "provider_probe": provider_probe,
        "worker": worker,
        "last_tick_at": last_tick,
    }
