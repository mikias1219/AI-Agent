"""Telegram, MCP, automations, reminders and status (Phase 6 split)."""

from __future__ import annotations

import hmac
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer
from personal_agent.application.services.telegram_activity import list_telegram_audit_activity
from personal_agent.domain.exceptions import AgentError
from personal_agent.infrastructure.integrations.telegram.runner import build_allowed_chats
from personal_agent.infrastructure.model_providers.runtime_selection import (
    hermes_installed,
    probe_ollama_reachable,
)
from personal_agent.presentation.web.routers._common import (
    DASHBOARD_OWNER,
    iso,
    telegram_foreign_runtime_active,
    telegram_runtime,
)


class ReminderCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    remind_at: datetime
    task_id: str | None = Field(default=None, max_length=64)
    channels: list[str] = Field(default_factory=lambda: ["inbox", "telegram"])


class AutomationPatchRequest(BaseModel):
    enabled: bool | None = None
    schedule_time: str | None = Field(default=None, max_length=8)
    channels: list[str] | None = None
    quiet_hours_start: str | None = Field(default=None, max_length=8)
    quiet_hours_end: str | None = Field(default=None, max_length=8)
    daily_cap: int | None = Field(default=None, ge=0, le=100)


class McpServerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    transport: str = Field(default="stdio", max_length=16)
    command: str = ""
    url: str = ""
    enabled: bool = True
    read_only: bool = False
    tool_allowlist: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=15.0, ge=1.0, le=120.0)
    max_output_bytes: int = Field(default=32768, ge=1024, le=200_000)


class McpServerPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    transport: str | None = Field(default=None, max_length=16)
    command: str | None = None
    url: str | None = None
    enabled: bool | None = None
    read_only: bool | None = None
    tool_allowlist: list[str] | None = None
    timeout_seconds: float | None = Field(default=None, ge=1.0, le=120.0)
    max_output_bytes: int | None = Field(default=None, ge=1024, le=200_000)


def build_integrations_router(
    container: AppContainer,
    *,
    production: bool,
    enforce_api_rate_limit: Callable[[Request], None],
) -> APIRouter:
    router = APIRouter(tags=["integrations"])

    def tick_secret() -> str:
        dedicated = container.settings.internal_tick_secret.strip()
        if dedicated or production:
            return dedicated
        return container.settings.dashboard_secret_key.strip()

    def reminder_payload(reminder: Any) -> dict[str, Any]:
        from personal_agent.domain.scheduler import Reminder

        assert isinstance(reminder, Reminder)
        return {
            "id": reminder.id,
            "text": reminder.text,
            "remind_at": iso(reminder.remind_at),
            "task_id": reminder.task_id,
            "channels": list(reminder.channels),
            "status": reminder.status.value,
            "late": reminder.late,
            "delivered_at": iso(reminder.delivered_at),
            "created_at": iso(reminder.created_at),
        }

    def automation_payload(row: Any) -> dict[str, Any]:
        from personal_agent.domain.scheduler import Automation

        assert isinstance(row, Automation)
        return {
            "id": row.id,
            "kind": row.kind,
            "enabled": row.enabled,
            "schedule_time": row.schedule_time,
            "channels": list(row.channels),
            "quiet_hours_start": row.quiet_hours_start,
            "quiet_hours_end": row.quiet_hours_end,
            "daily_cap": row.daily_cap,
            "last_run_at": iso(row.last_run_at),
            "last_result": row.last_result,
            "last_run_id": row.last_run_id,
        }

    def patch_automation_row(automation_id: str, request: AutomationPatchRequest) -> dict[str, Any]:
        row = container.automations.get(automation_id)
        if row is None or row.owner_user_id != DASHBOARD_OWNER:
            raise HTTPException(status_code=404, detail="Routine not found.")
        if request.enabled is not None:
            row.enabled = request.enabled
        if request.schedule_time is not None:
            if len(request.schedule_time.split(":")) != 2:
                raise HTTPException(status_code=400, detail="schedule_time must be HH:MM.")
            row.schedule_time = request.schedule_time
        if request.channels is not None:
            row.channels = request.channels
        if request.quiet_hours_start is not None:
            row.quiet_hours_start = request.quiet_hours_start.strip()
        if request.quiet_hours_end is not None:
            row.quiet_hours_end = request.quiet_hours_end.strip()
        if request.daily_cap is not None:
            row.daily_cap = request.daily_cap
        container.automations.save(row)
        return automation_payload(row)

    def run_automation_row(automation_id: str) -> dict[str, Any]:
        try:
            result = container.scheduler.run_automation_now(automation_id, DASHBOARD_OWNER)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        automation = result.get("automation")
        return {
            "processed": result.get("processed", 0),
            "automation": automation_payload(automation) if automation else None,
        }

    def mcp_payload(server: Any) -> dict[str, Any]:
        return {
            "id": server.id,
            "name": server.name,
            "transport": server.transport.value
            if hasattr(server.transport, "value")
            else server.transport,
            "command": server.command,
            "url": server.url,
            "enabled": server.enabled,
            "read_only": server.read_only,
            "tool_allowlist": list(server.tool_allowlist),
            "timeout_seconds": server.timeout_seconds,
            "max_output_bytes": server.max_output_bytes,
            "blocked_reason": container.mcp_adapter.blocked_reason(server),
        }

    def require_mcp_allowed(server: Any) -> None:
        reason = container.mcp_adapter.blocked_reason(server)
        if reason:
            raise HTTPException(status_code=400, detail=reason)

    def refresh_mcp_tools() -> int:
        from personal_agent.infrastructure.integrations.mcp.adapter import MCP_TOOL_PREFIX

        registry = container.registry
        unregister = getattr(registry, "unregister_prefix", None)
        if callable(unregister):
            unregister(MCP_TOOL_PREFIX)
        count = 0
        for server in container.mcp_servers.list():
            if not server.enabled:
                continue
            specs = container.mcp_adapter.discover(server)
            registry.register_all(specs)
            count += len(specs)
        return count

    @router.get("/api/status")
    def status() -> dict[str, Any]:
        current = container.settings
        model_name = (
            current.openai_compat_model
            if current.provider == "openai"
            else (current.hermes_model or current.ollama_model)
            if current.provider == "hermes"
            else current.ollama_model
            if current.provider == "ollama"
            else "offline fake"
        )
        return {
            "provider": current.provider,
            "model_setup": container.model_setup.read(),
            "model": model_name,
            "active_runtime": container.runtime.active_runtime,
            "runtime_reason": container.runtime.reason,
            "models": {
                "fast": current.model_fast or model_name,
                "smart": current.model_smart or model_name,
            },
            "hermes_installed": hermes_installed(current.hermes_directory),
            "ollama_reachable": probe_ollama_reachable(current.ollama_base_url),
            "telegram": {
                "configured": bool(current.telegram_bot_token),
                "allowed_chat_ids": sorted(build_allowed_chats(current.telegram_allowed_chat_ids)),
                "command": "personal-agent telegram",
                "managed": bool(container.telegram_worker and container.telegram_worker.running),
                **telegram_runtime(container),
            },
        }

    @router.post("/api/telegram/verify")
    def verify_telegram():
        try:
            identity = container.telegram.verify()
        except AgentError as exc:
            raise HTTPException(502, str(exc)) from exc
        container.audit.record(
            "telegram.identity_verified", "dashboard", {"username": identity.get("username")}
        )
        return identity

    @router.get("/api/telegram/activity")
    def telegram_activity(limit: int = Query(default=50, ge=1, le=200)):
        return list_telegram_audit_activity(container.audit, limit=limit)

    @router.post("/api/telegram/start")
    def start_telegram():
        worker = container.telegram_worker
        if worker is None:
            raise HTTPException(400, "Configure TELEGRAM_BOT_TOKEN in backend/.env and restart.")
        if telegram_foreign_runtime_active(container, worker):
            raise HTTPException(409, "A bot is already active in another process. Stop it first.")
        worker.start()
        container.audit.record("telegram.start_requested", "dashboard", {})
        container.onboarding.mark(DASHBOARD_OWNER, "briefing_ready")
        return {"requested": "start"}

    @router.post("/api/telegram/stop")
    def stop_telegram():
        if not container.telegram_worker or not container.telegram_worker.running:
            raise HTTPException(
                409, "No bot is owned by this dashboard. Stop a CLI bot in its terminal."
            )
        container.telegram_worker.stop()
        container.audit.record("telegram.stop_requested", "dashboard", {})
        return {"requested": "stop"}

    @router.post("/api/telegram/test")
    def test_telegram():
        allowed = build_allowed_chats(container.settings.telegram_allowed_chat_ids)
        if not container.settings.telegram_bot_token:
            raise HTTPException(400, "Configure TELEGRAM_BOT_TOKEN in backend/.env and restart.")
        if not allowed:
            raise HTTPException(400, "Add at least one chat id to TELEGRAM_ALLOWED_CHAT_IDS.")
        chat_id = next(iter(sorted(allowed)))
        try:
            container.telegram.send_message(
                chat_id, "AURA test: your Telegram connection is working."
            )
        except AgentError as exc:
            raise HTTPException(502, str(exc)) from exc
        container.audit.record("telegram.test_sent", "dashboard", {"chat_id": chat_id})
        return {"sent": True, "chat_id": chat_id}

    @router.post("/internal/tick")
    def internal_tick(request: Request) -> dict[str, Any]:
        provided = request.headers.get("X-Aura-Tick-Secret", "")
        expected = tick_secret()
        if not expected or not hmac.compare_digest(provided, expected):
            raise HTTPException(status_code=401, detail="Invalid tick secret.")
        return container.scheduler.tick()

    @router.get("/api/reminders")
    def list_reminders(
        status: Annotated[str | None, Query()] = None,
    ) -> list[dict[str, Any]]:
        from personal_agent.domain.scheduler import ReminderStatus

        status_n = None
        if status is not None:
            try:
                status_n = ReminderStatus(status)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return [
            reminder_payload(row)
            for row in container.reminders.list(DASHBOARD_OWNER, status=status_n)
        ]

    @router.post("/api/reminders", status_code=201)
    def create_reminder(request: ReminderCreateRequest) -> dict[str, Any]:
        try:
            reminder = container.scheduler.create_reminder(
                text=request.text,
                remind_at=request.remind_at
                if request.remind_at.tzinfo
                else request.remind_at.replace(tzinfo=UTC),
                owner_user_id=DASHBOARD_OWNER,
                task_id=request.task_id,
                channels=request.channels,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return reminder_payload(reminder)

    @router.get("/api/automations")
    def list_automations() -> list[dict[str, Any]]:
        return [automation_payload(row) for row in container.automations.list(DASHBOARD_OWNER)]

    @router.patch("/api/automations/{automation_id}")
    def patch_automation(automation_id: str, request: AutomationPatchRequest) -> dict[str, Any]:
        return patch_automation_row(automation_id, request)

    @router.post("/api/automations/{automation_id}/run")
    def run_automation(automation_id: str) -> dict[str, Any]:
        return run_automation_row(automation_id)

    @router.get("/api/routines")
    def list_routines() -> list[dict[str, Any]]:
        return list_automations()

    @router.patch("/api/routines/{automation_id}")
    def patch_routine(automation_id: str, request: AutomationPatchRequest) -> dict[str, Any]:
        return patch_automation_row(automation_id, request)

    @router.post("/api/routines/{automation_id}/run")
    def run_routine(automation_id: str) -> dict[str, Any]:
        return run_automation_row(automation_id)

    @router.get("/api/mcp/servers")
    def list_mcp_servers() -> list[dict[str, Any]]:
        return [mcp_payload(row) for row in container.mcp_servers.list()]

    @router.post("/api/mcp/servers", status_code=201)
    def create_mcp_server(http_request: Request, request: McpServerCreateRequest) -> dict[str, Any]:
        from personal_agent.domain.mcp import McpServer, McpTransport

        enforce_api_rate_limit(http_request)
        try:
            transport = McpTransport(request.transport)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="transport must be stdio or http.") from exc
        if transport is McpTransport.STDIO and not request.command.strip():
            raise HTTPException(status_code=400, detail="stdio servers require command.")
        if transport is McpTransport.HTTP and not request.url.strip():
            raise HTTPException(status_code=400, detail="http servers require url.")
        server = McpServer(
            id=uuid.uuid4().hex,
            name=request.name.strip(),
            transport=transport,
            command=request.command.strip(),
            url=request.url.strip(),
            enabled=request.enabled,
            read_only=request.read_only,
            tool_allowlist=list(request.tool_allowlist),
            timeout_seconds=request.timeout_seconds,
            max_output_bytes=request.max_output_bytes,
        )
        require_mcp_allowed(server)
        container.mcp_servers.save(server)
        tools = refresh_mcp_tools()
        container.audit.record("mcp.server_created", "dashboard", {"id": server.id, "tools": tools})
        payload = mcp_payload(server)
        payload["registered_tools"] = tools
        return payload

    @router.patch("/api/mcp/servers/{server_id}")
    def patch_mcp_server(server_id: str, request: McpServerPatchRequest) -> dict[str, Any]:
        from personal_agent.domain.mcp import McpTransport

        server = container.mcp_servers.get(server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found.")
        if request.name is not None:
            server.name = request.name.strip()
        if request.transport is not None:
            try:
                server.transport = McpTransport(request.transport)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400, detail="transport must be stdio or http."
                ) from exc
        if request.command is not None:
            server.command = request.command.strip()
        if request.url is not None:
            server.url = request.url.strip()
        if request.enabled is not None:
            server.enabled = request.enabled
        if request.read_only is not None:
            server.read_only = request.read_only
        if request.tool_allowlist is not None:
            server.tool_allowlist = list(request.tool_allowlist)
        if request.timeout_seconds is not None:
            server.timeout_seconds = request.timeout_seconds
        if request.max_output_bytes is not None:
            server.max_output_bytes = request.max_output_bytes
        if server.enabled:
            require_mcp_allowed(server)
        container.mcp_servers.save(server)
        tools = refresh_mcp_tools()
        payload = mcp_payload(server)
        payload["registered_tools"] = tools
        return payload

    @router.delete("/api/mcp/servers/{server_id}", status_code=204)
    def delete_mcp_server(server_id: str) -> Response:
        if container.mcp_servers.get(server_id) is None:
            raise HTTPException(status_code=404, detail="MCP server not found.")
        container.mcp_servers.delete(server_id)
        refresh_mcp_tools()
        return Response(status_code=204)

    @router.post("/api/mcp/servers/{server_id}/discover")
    def discover_mcp_server(http_request: Request, server_id: str) -> dict[str, Any]:
        enforce_api_rate_limit(http_request)
        server = container.mcp_servers.get(server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found.")
        require_mcp_allowed(server)
        specs = container.mcp_adapter.discover(server)
        tools = refresh_mcp_tools()
        return {
            "server_id": server_id,
            "discovered": [{"name": spec.name, "access_kind": spec.access_kind} for spec in specs],
            "registered_tools": tools,
        }

    return router
