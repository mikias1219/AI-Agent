"""Loopback-only web dashboard for chat and local agent operations."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import queue
import re
import secrets
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from personal_agent.app.container import AppContainer, build_app
from personal_agent.application.services.task_service import UNSET
from personal_agent.application.services.telegram_activity import list_telegram_audit_activity
from personal_agent.config.settings import Settings, load_settings
from personal_agent.domain.approvals import Approval, ApprovalStatus
from personal_agent.domain.dates import parse_due
from personal_agent.domain.exceptions import (
    AgentError,
    ApprovalConflictError,
    ApprovalForbiddenError,
    ConfigurationError,
    StorageError,
    ToolInputError,
)
from personal_agent.domain.memory import Memory, normalize_kind
from personal_agent.domain.models import (
    AgentRun,
    OwnerProfile,
    RunEvent,
    RunStatus,
    RunStep,
    Task,
    TaskPriority,
    TaskStatus,
)
from personal_agent.domain.task_rules import TaskView
from personal_agent.infrastructure.integrations.telegram.runner import build_allowed_chats
from personal_agent.infrastructure.model_providers.runtime_selection import (
    hermes_installed,
    probe_ollama_reachable,
)

logger = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).resolve().parents[5] / "frontend" / "dist"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})


def should_autostart_telegram(worker: object | None, allowed: frozenset[int]) -> bool:
    """Start the dashboard-owned worker when token wiring exists and chats are allowlisted."""
    return worker is not None and bool(allowed)


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    session_id: str | None = None


class RunStartRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    session_id: str | None = None


DASHBOARD_OWNER = "dashboard"


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=10_000)
    notes: str | None = Field(default=None, max_length=10_000)  # alias for description
    priority: TaskPriority = TaskPriority.NONE
    due_at: datetime | None = None  # naive values are read in the owner's timezone
    due: str | None = Field(default=None, max_length=128)  # plain words, e.g. "friday 3pm"
    project: str = Field(default="", max_length=128)
    tags: list[str] = Field(default_factory=list, max_length=20)


class TaskPatchRequest(BaseModel):
    """Partial update. Omitted fields are unchanged; `due_at`/`due` null clears the due date."""

    status: TaskStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=10_000)
    notes: str | None = Field(default=None, max_length=10_000)
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    due: str | None = Field(default=None, max_length=128)
    project: str | None = Field(default=None, max_length=128)
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Task title must be a non-empty string.")
        return value


class ProfilePatchRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    language: str | None = Field(default=None, min_length=1, max_length=16)


class ApprovalDecisionRequest(BaseModel):
    approve: bool


class ApprovalEditRequest(BaseModel):
    arguments: dict[str, Any]


class MemoryCreateRequest(BaseModel):
    kind: str = Field(default="fact", max_length=32)
    content: str = Field(min_length=1, max_length=2000)
    source_run_id: str | None = Field(default=None, max_length=64)


class MemoryPatchRequest(BaseModel):
    kind: str | None = Field(default=None, max_length=32)
    content: str | None = Field(default=None, min_length=1, max_length=2000)


class MemoryForgetAllRequest(BaseModel):
    token: str = Field(min_length=8, max_length=256)
    confirm_phrase: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)
    email: str = Field(default="", max_length=254)


class RegistrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=1024)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _task_payload(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "notes": task.description,
        "status": task.status.value,
        "owner_user_id": task.owner_user_id,
        "priority": task.priority.value,
        "due_at": _iso(task.due_at),
        "project": task.project,
        "tags": list(task.tags),
        "source": task.source,
        "source_ref": task.source_ref,
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
        "completed_at": _iso(task.completed_at),
        "deleted_at": _iso(task.deleted_at),
    }


def _run_payload(run: AgentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "session_id": run.session_id,
        "origin": run.origin,
        "status": run.status.value,
        "prompt_version": run.prompt_version,
        "model": run.model,
        "input": run.input_text,
        "reply": run.final_text,
        "error": run.error,
        "stop_reason": run.stop_reason,
        "created_at": _iso(run.created_at),
        "finished_at": _iso(run.finished_at),
    }


def _step_payload(step: RunStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "seq": step.seq,
        "kind": step.kind,
        "name": step.name,
        "status": step.status.value,
        "arguments": step.arguments,
        "output": step.output,
        "error": step.error,
        "started_at": _iso(step.started_at),
        "finished_at": _iso(step.finished_at),
        "duration_ms": step.duration_ms,
    }


def _event_line(event: RunEvent) -> str:
    return (
        json.dumps(
            {"seq": event.seq, "run_id": event.run_id, "type": event.type, "data": event.data},
            ensure_ascii=False,
            default=str,
        )
        + "\n"
    )


def _approval_payload(approval: Approval, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    return {
        "id": approval.id,
        "run_id": approval.run_id,
        "session_id": approval.session_id,
        "tool_name": approval.tool_name,
        "summary": approval.summary,
        "arguments": approval.arguments,
        "arguments_hash": approval.arguments_hash,
        "risk": approval.risk,
        "untrusted_content": approval.untrusted_content,
        "status": approval.status.value,
        "origin": approval.origin,
        "user_id": approval.user_id,
        "created_at": _iso(approval.created_at),
        "expires_at": _iso(approval.expires_at),
        "decided_at": _iso(approval.decided_at),
        "decided_by": approval.decided_by,
        "channel": approval.channel,
        "result": approval.result,
        "edited_from": approval.edited_from,
        "actionable": approval.status is ApprovalStatus.PENDING and not approval.is_expired(now),
    }


def _profile_payload(profile: OwnerProfile) -> dict[str, Any]:
    return {
        "name": profile.name,
        "timezone": profile.timezone,
        "language": profile.language,
        "wizard_completed": profile.wizard_completed,
    }


class WizardCompleteRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class ReminderCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    remind_at: datetime
    task_id: str | None = Field(default=None, max_length=64)
    channels: list[str] = Field(default_factory=lambda: ["inbox", "telegram"])


class GoogleSettingsPatchRequest(BaseModel):
    read_only: bool


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


class AutomationPatchRequest(BaseModel):
    enabled: bool | None = None
    schedule_time: str | None = Field(default=None, max_length=8)
    channels: list[str] | None = None


def create_dashboard_app(
    *,
    container: AppContainer | None = None,
    settings: Settings | None = None,
    frontend_dir: Path | None = None,
) -> FastAPI:
    """Create the dashboard API and page; the CLI binds its server to loopback only."""
    settings = settings or (container.settings if container else load_settings())
    if len(settings.dashboard_secret_key) < 32:
        raise ConfigurationError(
            "Run personal-agent init-dashboard from backend/ before starting the dashboard."
        )
    container = container or build_app(settings=settings)

    frontend_dir = frontend_dir or FRONTEND_DIR
    react_index = frontend_dir / "index.html"

    def session_key() -> str:
        return container.auth.session_key(settings.dashboard_secret_key)

    @asynccontextmanager
    async def lifespan(_app):
        worker = container.telegram_worker
        allowed = build_allowed_chats(container.settings.telegram_allowed_chat_ids)
        if should_autostart_telegram(worker, allowed):
            if telegram_foreign_runtime_active(container, worker):
                logger.info("Skipping Telegram auto-start: another process is already polling.")
            else:
                try:
                    await asyncio.to_thread(worker.start)
                except Exception:
                    logger.exception("Telegram auto-start failed")
        stop_sweeper = threading.Event()

        def sweep_expired() -> None:
            # APR-05: expire overdue approvals now (restart case) and then every minute.
            while True:
                try:
                    container.approval_service.expire_due()
                except Exception:  # noqa: BLE001 — never let the sweeper die
                    logger.exception("Approval expiry sweep failed")
                if stop_sweeper.wait(60):
                    return

        threading.Thread(target=sweep_expired, daemon=True, name="approval-expiry").start()
        stop_scheduler = threading.Event()

        def scheduler_loop() -> None:
            # AUT-01: process due jobs locally even when GitHub Actions cannot reach us.
            while True:
                try:
                    container.scheduler.tick()
                except Exception:  # noqa: BLE001
                    logger.exception("Scheduler tick failed")
                if stop_scheduler.wait(30):
                    return

        threading.Thread(target=scheduler_loop, daemon=True, name="scheduler-tick").start()
        yield
        stop_sweeper.set()
        stop_scheduler.set()
        if worker:
            await asyncio.to_thread(worker.close)

    app = FastAPI(
        title="Personal Agent Dashboard", docs_url=None, redoc_url=None, lifespan=lifespan
    )
    app.state.container = container
    app.state.login_failures = {}
    app.state.login_lock = threading.Lock()
    production = settings.environment == "production"
    cookie_secure = production
    # Production SPA is same-origin via the Vercel /api proxy, so Lax keeps the
    # session cookie first-party (cross-site SameSite=None is blocked in many browsers).
    cookie_samesite = "lax" if production else "strict"
    allowed_origins = _allowed_browser_origins(settings)

    @app.middleware("http")
    async def restrict_browser_access(request, call_next):  # noqa: ANN001
        host_header = request.headers.get("host", "")
        host = urlsplit(f"//{host_header}").hostname
        if not production and host not in LOCAL_HOSTS:
            return JSONResponse({"detail": "Dashboard accepts local connections only."}, 400)
        origin = request.headers.get("origin")
        request_origins = set(allowed_origins)
        if host_header:
            request_origins.add(f"http://{host_header}")
            request_origins.add(f"https://{host_header}")
        if origin and not _origin_allowed(origin, request_origins, production=production):
            return JSONResponse({"detail": "Cross-origin requests are not allowed."}, 403)
        # Let CORSMiddleware answer browser preflights; do not require a session cookie.
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        response: Response
        public = path in {
            "/",
            "/login",
            "/api/login",
            "/api/register",
            "/api/auth",
            "/api/health",
            "/api/google/callback",
            "/internal/tick",
        }
        public = public or path.startswith("/assets/")
        if not public and not _valid_dashboard_session(request, session_key()):
            response = JSONResponse({"detail": "Login required."}, 401)
        else:
            response = await call_next(request)
        if path.startswith("/api/") or path in {"/", "/login"}:
            response.headers["Cache-Control"] = "no-store"
        connect_src = "'self'"
        for origin in sorted(_configured_frontend_origins(settings)):
            connect_src = f"{connect_src} {origin}"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            f"connect-src {connect_src}; img-src 'self' data:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/assets/{asset_path:path}", include_in_schema=False)
    def frontend_asset(asset_path: str) -> FileResponse:
        root = (frontend_dir / "assets").resolve()
        candidate = (root / asset_path).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise HTTPException(404, "Asset not found.")
        return FileResponse(candidate)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        if not react_index.is_file():
            raise HTTPException(
                503, "Build the UI from the repository root: npm --prefix frontend run build"
            )
        return FileResponse(react_index)

    @app.get("/login", include_in_schema=False)
    def login_page() -> FileResponse:
        return index()

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        current = container.settings
        database_url = current.database_url.lower()
        if "postgres" in database_url:
            storage = "postgres"
        elif database_url.startswith("sqlite"):
            storage = "sqlite"
        else:
            storage = "other"
        installed = hermes_installed(current.hermes_directory)
        return {
            "status": "ok",
            "environment": current.environment,
            "provider": current.provider,
            "model": (
                current.openai_compat_model
                if current.provider == "openai"
                else (current.hermes_model or current.ollama_model)
                if current.provider == "hermes"
                else current.ollama_model
                if current.provider == "ollama"
                else "offline fake"
            ),
            "storage": storage,
            "hermes_ready": installed,
            "hermes_installed": installed,
            "active_runtime": container.runtime.active_runtime,
            "runtime_reason": container.runtime.reason,
            "ollama_reachable": probe_ollama_reachable(current.ollama_base_url),
            "frontend_origin_configured": bool(current.frontend_origin),
        }

    @app.get("/api/auth")
    def auth_status(request: Request) -> dict[str, Any]:
        authenticated = _valid_dashboard_session(request, session_key())
        return {
            "authenticated": authenticated,
            "registered": container.auth.registered(),
            "user": container.auth.profile() if authenticated else None,
            "email_required": container.auth.requires_email(),
        }

    @app.post("/api/login")
    def login(request: Request, credentials: LoginRequest):
        remote_addr = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with app.state.login_lock:
            failures, locked_until = app.state.login_failures.get(remote_addr, (0, 0.0))
            if now < locked_until:
                raise HTTPException(status_code=429, detail="Too many attempts. Try again shortly.")
        if not container.auth.verify(credentials.password, credentials.email):
            with app.state.login_lock:
                failures, _ = app.state.login_failures.get(remote_addr, (0, 0.0))
                failures += 1
                app.state.login_failures[remote_addr] = (
                    0 if failures >= 5 else failures,
                    now + 60 if failures >= 5 else 0.0,
                )
            raise HTTPException(status_code=401, detail="Incorrect password.")
        with app.state.login_lock:
            app.state.login_failures.pop(remote_addr, None)
        response = JSONResponse({"authenticated": True, "user": container.auth.profile()})
        response.set_cookie(
            "personal_agent_session",
            _create_dashboard_session(session_key()),
            max_age=12 * 60 * 60,
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
            path="/",
        )
        return response

    @app.post("/api/register", status_code=201)
    def register(credentials: RegistrationRequest):
        try:
            container.auth.register(credentials.name, credentials.email, credentials.password)
        except StorageError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        container.audit.record("workspace.registered", "dashboard", {})
        return {"registered": True}

    @app.post("/api/logout")
    def logout():
        response = JSONResponse({"authenticated": False})
        response.delete_cookie(
            "personal_agent_session",
            path="/",
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
        )
        return response

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        current = container.settings
        return {
            "provider": current.provider,
            "model_setup": container.model_setup.read(),
            "model": (
                current.openai_compat_model
                if current.provider == "openai"
                else (current.hermes_model or current.ollama_model)
                if current.provider == "hermes"
                else current.ollama_model
                if current.provider == "ollama"
                else "offline fake"
            ),
            "active_runtime": container.runtime.active_runtime,
            "runtime_reason": container.runtime.reason,
            "hermes_installed": hermes_installed(current.hermes_directory),
            "ollama_reachable": probe_ollama_reachable(current.ollama_base_url),
            "telegram": {
                "configured": bool(current.telegram_bot_token),
                "allowed_chat_ids": sorted(build_allowed_chats(current.telegram_allowed_chat_ids)),
                "command": "personal-agent telegram",
                "managed": bool(container.telegram_worker and container.telegram_worker.running),
                **_telegram_runtime(container),
            },
        }

    @app.post("/api/telegram/verify")
    def verify_telegram():
        try:
            identity = container.telegram.verify()
        except AgentError as exc:
            raise HTTPException(502, str(exc)) from exc
        container.audit.record(
            "telegram.identity_verified", "dashboard", {"username": identity.get("username")}
        )
        return identity

    @app.get("/api/telegram/activity")
    def telegram_activity(limit: int = Query(default=50, ge=1, le=200)):
        return list_telegram_audit_activity(container.audit, limit=limit)

    @app.post("/api/telegram/start")
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

    @app.post("/api/telegram/stop")
    def stop_telegram():
        if not container.telegram_worker or not container.telegram_worker.running:
            raise HTTPException(
                409, "No bot is owned by this dashboard. Stop a CLI bot in its terminal."
            )
        container.telegram_worker.stop()
        container.audit.record("telegram.stop_requested", "dashboard", {})
        return {"requested": "stop"}

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> dict[str, str]:
        try:
            session_id, reply = container.chat.turn(
                user_id="dashboard",
                session_id=request.session_id,
                text=request.text,
                origin="dashboard",
            )
        except AgentError as exc:
            logger.exception("Dashboard chat request failed")
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"session_id": session_id, "reply": reply}

    @app.post("/api/chat/stream")
    def stream_chat(request: ChatRequest) -> StreamingResponse:
        events: queue.SimpleQueue = queue.SimpleQueue()
        disconnected = threading.Event()

        def token(text: str) -> None:
            if disconnected.is_set():
                raise AgentError("The response connection closed.")
            events.put({"type": "delta", "text": text})

        def generate() -> None:
            try:
                session_id, reply = container.chat.turn(
                    user_id="dashboard",
                    session_id=request.session_id,
                    text=request.text,
                    origin="dashboard",
                    on_token=token,
                )
                events.put({"type": "done", "session_id": session_id, "reply": reply})
            except AgentError as exc:
                events.put({"type": "error", "detail": str(exc)})
            except Exception:
                logger.exception("Streaming chat failed")
                events.put({"type": "error", "detail": "The agent could not complete this reply."})
            finally:
                events.put(None)

        def body():
            threading.Thread(target=generate, daemon=True, name="chat-stream").start()
            try:
                while True:
                    event = events.get()
                    if event is None:
                        break
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            finally:
                disconnected.set()

        return StreamingResponse(
            body(),
            media_type="application/x-ndjson",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
        )

    def _own_run(run_id: str) -> AgentRun:
        try:
            run = container.runs.get(run_id)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail="Run not found.") from exc
        if run.user_id != DASHBOARD_OWNER:
            raise HTTPException(status_code=404, detail="Run not found.")
        return run

    @app.post("/api/runs", status_code=202)
    def start_run(request: RunStartRequest) -> dict[str, Any]:
        """Accept a chat turn and run it in the background; follow it via /events."""
        try:
            run = container.runs.start(
                user_id=DASHBOARD_OWNER,
                text=request.text,
                session_id=request.session_id,
                origin="dashboard",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _run_payload(run)

    @app.get("/api/runs")
    def list_runs(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return [
            _run_payload(run) for run in container.runs.list_recent(DASHBOARD_OWNER, limit=limit)
        ]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        run = _own_run(run_id)
        steps = container.runs.steps(run.id)
        return {
            **_run_payload(run),
            "steps": [_step_payload(step) for step in steps],
            "approvals": [
                _approval_payload(item) for item in container.approval_service.for_run(run.id)
            ],
        }

    @app.get("/api/runs/{run_id}/events")
    def run_events(run_id: str, after: int = Query(default=0, ge=0)) -> StreamingResponse:
        """NDJSON event stream: replays from `after`, follows live, ends at run.completed/failed."""
        _own_run(run_id)

        def body():
            for event in container.runs.events(run_id, after_seq=after):
                # A blank line is a keep-alive; writing it surfaces client disconnects.
                yield "\n" if event is None else _event_line(event)

        return StreamingResponse(
            body(),
            media_type="application/x-ndjson",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
        )

    @app.post("/api/runs/{run_id}/cancel", status_code=202)
    def cancel_run(run_id: str) -> dict[str, Any]:
        """Ask the run to stop before its next step; finished runs are returned unchanged."""
        run = _own_run(run_id)
        if run.status is RunStatus.AWAITING_APPROVAL:
            # A paused run has no thread to stop: deny its pending approvals to end it.
            for item in container.approval_service.for_run(run_id):
                if item.status is ApprovalStatus.PENDING:
                    container.approval_service.decide(
                        item.id, False, actor=DASHBOARD_OWNER, channel="dashboard"
                    )
            return _run_payload(_own_run(run_id))
        return _run_payload(container.runs.cancel(run_id))

    @app.get("/api/conversations")
    def conversations(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return [
            {
                "id": item.id,
                "user_id": item.user_id,
                "created_at": item.created_at.isoformat(),
            }
            for item in container.conversations.list_sessions(limit=limit)
        ]

    @app.get("/api/conversations/{session_id}/messages")
    def conversation_messages(
        session_id: str, limit: int = Query(default=100, ge=1, le=500)
    ) -> list[dict[str, Any]]:
        return [
            {
                "role": message.role,
                "content": message.content,
                "name": message.name,
                "tool_call_id": message.tool_call_id,
                "tool_calls": [
                    {"id": call.id, "name": call.name, "arguments": call.arguments}
                    for call in message.tool_calls
                ],
            }
            for message in container.conversations.load(session_id, limit=limit)
        ]

    def _due_from(due_at: datetime | None, due: str | None) -> datetime | None:
        """Resolve an explicit datetime or plain-words due date in the owner's timezone."""
        timezone = container.profiles.timezone_for(DASHBOARD_OWNER)
        if due is not None and due.strip():
            return parse_due(due, timezone)
        if due_at is not None:
            return parse_due(due_at.isoformat(), timezone)
        return None

    def _task_or_404(task_id: str) -> Task:
        task = container.tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        return task

    def _task_error(exc: Exception) -> HTTPException:
        missing = isinstance(exc, StorageError) and "unknown task" in str(exc).lower()
        return HTTPException(status_code=404 if missing else 400, detail=str(exc))

    @app.get("/api/tasks")
    def tasks(
        view: Annotated[TaskView | None, Query()] = None,
        status: Annotated[TaskStatus | None, Query()] = None,
        priority: Annotated[TaskPriority | None, Query()] = None,
        project: str | None = Query(default=None, max_length=128),
        tag: str | None = Query(default=None, max_length=64),
        q: str | None = Query(default=None, max_length=256),
        include_deleted: bool = Query(default=False),
    ) -> list[dict[str, Any]]:
        timezone = container.profiles.timezone_for(DASHBOARD_OWNER)
        if q is not None and q.strip():
            found = container.tasks.search(q, include_deleted=include_deleted)
            if status is not None:
                found = [t for t in found if t.status is status]
            if view is not None:
                in_view = {t.id for t in container.tasks.list(status, view=view, timezone=timezone)}
                found = [t for t in found if t.id in in_view]
        else:
            found = container.tasks.list(
                status, view=view, include_deleted=include_deleted, timezone=timezone
            )
        if priority is not None:
            found = [t for t in found if t.priority is priority]
        if project is not None:
            found = [t for t in found if t.project.lower() == project.lower()]
        if tag is not None:
            found = [t for t in found if tag.lower() in (x.lower() for x in t.tags)]
        return [_task_payload(task) for task in found]

    @app.post("/api/tasks", status_code=201)
    def create_task(request: TaskCreateRequest) -> dict[str, Any]:
        try:
            task_id = container.tasks.create(
                title=request.title.strip(),
                description=(
                    request.notes if request.notes is not None else request.description
                ).strip(),
                owner_user_id=DASHBOARD_OWNER,
                priority=request.priority,
                due_at=_due_from(request.due_at, request.due),
                project=request.project,
                tags=request.tags,
                source="manual",
            )
            task = container.tasks.get(task_id)
        except (AgentError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if task is None:
            raise HTTPException(status_code=500, detail="Created task could not be reloaded.")
        return _task_payload(task)

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, Any]:
        return _task_payload(_task_or_404(task_id))

    @app.patch("/api/tasks/{task_id}")
    def patch_task(task_id: str, request: TaskPatchRequest) -> dict[str, Any]:
        sent = request.model_fields_set
        try:
            fields: dict[str, Any] = {}
            if request.title is not None:
                fields["title"] = request.title
            notes = request.notes if request.notes is not None else request.description
            if notes is not None:
                fields["description"] = notes
            if request.priority is not None:
                fields["priority"] = request.priority
            if request.project is not None:
                fields["project"] = request.project
            if request.tags is not None:
                fields["tags"] = request.tags
            if sent & {"due_at", "due"}:
                fields["due_at"] = _due_from(request.due_at, request.due)
            _task_or_404(task_id)
            if request.status is not None:
                container.tasks.advance(task_id, request.status)
            if fields:
                container.tasks.update(task_id, **fields)
        except (AgentError, ValueError) as exc:
            raise _task_error(exc) from exc
        return _task_payload(_task_or_404(task_id))

    @app.post("/api/tasks/{task_id}/reopen")
    def reopen_task(task_id: str) -> dict[str, Any]:
        try:
            container.tasks.reopen(task_id)
        except (AgentError, ValueError) as exc:
            raise _task_error(exc) from exc
        return _task_payload(_task_or_404(task_id))

    @app.delete("/api/tasks/{task_id}")
    def delete_task(task_id: str) -> dict[str, Any]:
        try:
            container.tasks.soft_delete(task_id)
        except (AgentError, ValueError) as exc:
            raise _task_error(exc) from exc
        return {"id": task_id, "deleted": True}

    @app.get("/api/profile")
    def get_profile() -> dict[str, Any]:
        return _profile_payload(container.profiles.get(DASHBOARD_OWNER))

    @app.patch("/api/profile")
    def patch_profile(request: ProfilePatchRequest) -> dict[str, Any]:
        sent = request.model_fields_set
        try:
            profile = container.profiles.update(
                DASHBOARD_OWNER,
                name=request.name if "name" in sent else UNSET,
                timezone=request.timezone if request.timezone is not None else UNSET,
                language=request.language if request.language is not None else UNSET,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _profile_payload(profile)

    @app.get("/api/onboarding")
    def get_onboarding() -> dict[str, Any]:
        return container.onboarding.payload(DASHBOARD_OWNER)

    @app.post("/api/onboarding/wizard")
    def complete_wizard(request: WizardCompleteRequest) -> dict[str, Any]:
        try:
            return container.onboarding.complete_wizard(
                DASHBOARD_OWNER, name=request.name, timezone=request.timezone
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/onboarding/skip-briefing")
    def skip_briefing() -> dict[str, Any]:
        return container.onboarding.skip_briefing(DASHBOARD_OWNER)

    def _tick_secret() -> str:
        return (
            container.settings.internal_tick_secret or container.settings.dashboard_secret_key
        ).strip()

    @app.post("/internal/tick")
    def internal_tick(request: Request) -> dict[str, Any]:
        """Protected scheduler tick for GitHub Actions (AUT-01)."""
        provided = request.headers.get("X-Aura-Tick-Secret", "")
        expected = _tick_secret()
        if not expected or not hmac.compare_digest(provided, expected):
            raise HTTPException(status_code=401, detail="Invalid tick secret.")
        return container.scheduler.tick()

    def _reminder_payload(reminder: Any) -> dict[str, Any]:
        from personal_agent.domain.scheduler import Reminder

        assert isinstance(reminder, Reminder)
        return {
            "id": reminder.id,
            "text": reminder.text,
            "remind_at": _iso(reminder.remind_at),
            "task_id": reminder.task_id,
            "channels": list(reminder.channels),
            "status": reminder.status.value,
            "late": reminder.late,
            "delivered_at": _iso(reminder.delivered_at),
            "created_at": _iso(reminder.created_at),
        }

    @app.get("/api/reminders")
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
            _reminder_payload(row)
            for row in container.reminders.list(DASHBOARD_OWNER, status=status_n)
        ]

    @app.post("/api/reminders", status_code=201)
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
        return _reminder_payload(reminder)

    def _automation_payload(row: Any) -> dict[str, Any]:
        from personal_agent.domain.scheduler import Automation

        assert isinstance(row, Automation)
        return {
            "id": row.id,
            "kind": row.kind,
            "enabled": row.enabled,
            "schedule_time": row.schedule_time,
            "channels": list(row.channels),
            "last_run_at": _iso(row.last_run_at),
            "last_result": row.last_result,
            "last_run_id": row.last_run_id,
        }

    @app.get("/api/automations")
    def list_automations() -> list[dict[str, Any]]:
        return [_automation_payload(row) for row in container.automations.list(DASHBOARD_OWNER)]

    @app.patch("/api/automations/{automation_id}")
    def patch_automation(automation_id: str, request: AutomationPatchRequest) -> dict[str, Any]:
        row = container.automations.get(automation_id)
        if row is None or row.owner_user_id != DASHBOARD_OWNER:
            raise HTTPException(status_code=404, detail="Automation not found.")
        if request.enabled is not None:
            row.enabled = request.enabled
        if request.schedule_time is not None:
            if len(request.schedule_time.split(":")) != 2:
                raise HTTPException(status_code=400, detail="schedule_time must be HH:MM.")
            row.schedule_time = request.schedule_time
        if request.channels is not None:
            row.channels = request.channels
        container.automations.save(row)
        return _automation_payload(row)

    @app.post("/api/automations/{automation_id}/run")
    def run_automation(automation_id: str) -> dict[str, Any]:
        try:
            result = container.scheduler.run_automation_now(automation_id, DASHBOARD_OWNER)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        automation = result.get("automation")
        return {
            "processed": result.get("processed", 0),
            "automation": _automation_payload(automation) if automation else None,
        }

    @app.get("/api/briefing/latest")
    def latest_briefing() -> dict[str, Any]:
        text = container.scheduler.latest_briefing(DASHBOARD_OWNER)
        return {"text": text}

    @app.get("/api/activity")
    def activity(
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, Any]]:
        return container.audit.list_recent(limit=limit, offset=offset)

    @app.get("/api/approvals")
    def approvals(
        status: str = Query(default="pending"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        wanted: ApprovalStatus | None
        try:
            wanted = None if status == "all" else ApprovalStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Unknown approval status.") from exc
        return [
            _approval_payload(item)
            for item in container.approval_service.list_approvals(wanted, limit=limit)
        ]

    def _approval_error(exc: Exception) -> HTTPException:
        if isinstance(exc, ApprovalForbiddenError):
            return HTTPException(status_code=403, detail=str(exc))
        if isinstance(exc, ApprovalConflictError):
            return HTTPException(status_code=409, detail=str(exc))
        if isinstance(exc, ToolInputError):
            return HTTPException(status_code=422, detail=str(exc))
        return HTTPException(status_code=404, detail="Approval not found.")

    @app.get("/api/approvals/{approval_id}")
    def get_approval(approval_id: str) -> dict[str, Any]:
        try:
            return _approval_payload(container.approval_service.get(approval_id))
        except StorageError as exc:
            raise _approval_error(exc) from exc

    @app.post("/api/approvals/{approval_id}/decision")
    def decide_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, Any]:
        """Approve (runs the tool once and resumes the run) or deny. Idempotent."""
        try:
            outcome = container.approval_service.decide(
                approval_id, request.approve, actor=DASHBOARD_OWNER, channel="dashboard"
            )
        except (StorageError, ApprovalForbiddenError, ApprovalConflictError) as exc:
            raise _approval_error(exc) from exc
        return {
            "id": approval_id,
            "decision": outcome.decision,
            "status": outcome.approval.status.value,
            "executed": outcome.executed,
            "ok": outcome.ok,
            "result": outcome.output,
            "run_id": outcome.approval.run_id,
            "approval": _approval_payload(outcome.approval),
        }

    @app.post("/api/approvals/{approval_id}/edit", status_code=201)
    def edit_approval(approval_id: str, request: ApprovalEditRequest) -> dict[str, Any]:
        """Edit-then-approve: supersedes this approval with a new one (new hash) to approve."""
        try:
            replacement = container.approval_service.edit(
                approval_id, request.arguments, actor=DASHBOARD_OWNER, channel="dashboard"
            )
        except (
            StorageError,
            ApprovalForbiddenError,
            ApprovalConflictError,
            ToolInputError,
        ) as exc:
            raise _approval_error(exc) from exc
        return _approval_payload(replacement)

    def _memory_payload(memory: Memory) -> dict[str, Any]:
        return {
            "id": memory.id,
            "kind": memory.kind,
            "content": memory.content,
            "source_run_id": memory.source_run_id,
            "last_used_at": _iso(memory.last_used_at),
            "created_at": _iso(memory.created_at),
        }

    @app.get("/api/memories")
    def list_memories(
        kind: Annotated[str | None, Query()] = None,
        q: Annotated[str | None, Query(max_length=256)] = None,
    ) -> list[dict[str, Any]]:
        kind_n = None
        if kind is not None:
            try:
                kind_n = normalize_kind(kind)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return [
            _memory_payload(m) for m in container.memories.list(DASHBOARD_OWNER, kind=kind_n, q=q)
        ]

    @app.get("/api/memories/search")
    def search_memories(
        q: Annotated[str, Query(min_length=1, max_length=500)],
    ) -> list[dict[str, Any]]:
        return [_memory_payload(m) for m in container.memories.search(DASHBOARD_OWNER, q)]

    @app.post("/api/memories/forget-all/token")
    def forget_all_token() -> dict[str, str]:
        return container.memories.issue_forget_token(DASHBOARD_OWNER)

    @app.post("/api/memories/forget-all")
    def forget_all(request: MemoryForgetAllRequest) -> dict[str, Any]:
        try:
            count = container.memories.forget_all(
                DASHBOARD_OWNER,
                token=request.token,
                confirm_phrase=request.confirm_phrase,
            )
        except AgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"deleted": count}

    @app.post("/api/memories", status_code=201)
    def create_memory(request: MemoryCreateRequest) -> dict[str, Any]:
        try:
            memory = container.memories.create(
                DASHBOARD_OWNER,
                request.kind,
                request.content,
                source_run_id=request.source_run_id,
                actor=DASHBOARD_OWNER,
            )
        except (AgentError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _memory_payload(memory)

    @app.get("/api/memories/{memory_id}")
    def get_memory(memory_id: str) -> dict[str, Any]:
        memory = container.memories.get(memory_id)
        if memory is None or memory.user_id != DASHBOARD_OWNER:
            raise HTTPException(status_code=404, detail="Memory not found.")
        return _memory_payload(memory)

    @app.patch("/api/memories/{memory_id}")
    def patch_memory(memory_id: str, request: MemoryPatchRequest) -> dict[str, Any]:
        fields: dict[str, str] = {}
        if request.content is not None:
            fields["content"] = request.content
        if request.kind is not None:
            fields["kind"] = request.kind
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update.")
        try:
            memory = container.memories.update(memory_id, DASHBOARD_OWNER, **fields)
        except (StorageError, AgentError, ValueError) as exc:
            status = 404 if isinstance(exc, StorageError) else 400
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return _memory_payload(memory)

    @app.delete("/api/memories/{memory_id}", status_code=204)
    def delete_memory(memory_id: str) -> Response:
        try:
            container.memories.delete(memory_id, DASHBOARD_OWNER)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return Response(status_code=204)

    def _google_oauth_configured() -> bool:
        return bool(container.settings.google_client_id and container.settings.google_client_secret)

    def _google_oauth(*, read_only: bool = True) -> Any:
        from personal_agent.infrastructure.integrations.google.oauth import (
            GoogleOAuthClient,
            scopes_for_read_only,
        )

        return GoogleOAuthClient(
            client_id=container.settings.google_client_id,
            client_secret=container.settings.google_client_secret,
            redirect_uri=container.settings.google_redirect_uri,
        ), scopes_for_read_only(read_only)

    from personal_agent.infrastructure.integrations.google.session import (
        GoogleNotConnectedError,
        make_access_token_provider,
    )

    _google_token_provider = make_access_token_provider(
        store=container.google, settings=container.settings
    )

    def _google_access_token() -> str:
        try:
            return _google_token_provider()
        except GoogleNotConnectedError as exc:
            message = str(exc)
            if "Connect Google under Connections" in message:
                message = "Google is not connected. Connect from Connections first."
            raise HTTPException(400, message) from None

    def _google_auth_url(*, read_only: bool) -> str:
        from urllib.parse import urlencode

        scopes = _google_oauth(read_only=read_only)[1]
        params = urlencode(
            {
                "client_id": container.settings.google_client_id,
                "redirect_uri": container.settings.google_redirect_uri,
                "response_type": "code",
                "scope": " ".join(scopes),
                "access_type": "offline",
                "prompt": "consent",
                "state": "ro=1" if read_only else "ro=0",
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    @app.get("/api/google/status")
    def google_status() -> dict[str, Any]:
        return container.google.status(oauth_configured=_google_oauth_configured())

    @app.post("/api/google/connect")
    def google_connect(
        read_only: Annotated[bool, Query()] = True,
    ) -> dict[str, Any]:
        if not _google_oauth_configured():
            raise HTTPException(
                400,
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env "
                "(free Google Cloud OAuth client), then restart.",
            )
        auth_url = _google_auth_url(read_only=read_only)
        container.google.set_read_only(read_only)
        container.audit.record("google.connect_started", "dashboard", {"read_only": read_only})
        return {"auth_url": auth_url, "local_dev_connected": False, "read_only": read_only}

    @app.patch("/api/google/settings")
    def google_settings_patch(request: GoogleSettingsPatchRequest) -> dict[str, Any]:
        if not _google_oauth_configured():
            raise HTTPException(400, "Google OAuth is not configured.")
        status = container.google.status(oauth_configured=True)
        if not status.get("connected"):
            raise HTTPException(400, "Connect Google before changing settings.")
        wants_write = not request.read_only
        currently_ro = bool(status.get("read_only", True))
        container.google.set_read_only(request.read_only)
        auth_url = None
        if wants_write and currently_ro:
            # Re-consent for write scopes when leaving Read-only.
            auth_url = _google_auth_url(read_only=False)
        container.audit.record(
            "google.settings_patched",
            "dashboard",
            {"read_only": request.read_only, "reconsent": bool(auth_url)},
        )
        next_status = container.google.status(oauth_configured=True)
        if auth_url:
            next_status["auth_url"] = auth_url
        return next_status

    @app.get("/api/google/callback")
    def google_callback(
        code: str = Query(default=""),
        error: str = Query(default=""),
        state: str = Query(default=""),
    ):
        from personal_agent.infrastructure.integrations.google.oauth import GoogleOAuthError

        if error:
            raise HTTPException(400, f"Google OAuth error: {error}")
        if not code:
            raise HTTPException(400, "Missing OAuth code.")
        if not _google_oauth_configured():
            raise HTTPException(400, "Google OAuth is not configured.")
        read_only = "ro=0" not in state
        oauth, scopes = _google_oauth(read_only=read_only)
        try:
            token_payload = oauth.exchange_code(code)
            access = token_payload["access_token"]
            refresh = token_payload.get("refresh_token") or ""
            info = oauth.userinfo(access)
            email = str(info.get("email") or "google-oauth-user")
            # Preserve existing refresh token if Google omits it on re-consent.
            if not refresh:
                existing = container.google.load_tokens()
                refresh = existing.get("refresh_token") or ""
            container.google.save_tokens(
                email=email,
                access_token=access,
                refresh_token=refresh,
                scopes=token_payload.get("scope") or " ".join(scopes),
                read_only=read_only,
            )
        except GoogleOAuthError as exc:
            raise HTTPException(400, str(exc)) from exc
        container.audit.record(
            "google.oauth_callback",
            "dashboard",
            {"email": email, "read_only": read_only},
        )
        return Response(
            content=(
                "<html><body style='font-family:sans-serif;padding:2rem'>"
                "<h1>Google connected</h1>"
                "<p>You can close this tab and return to AURA.</p>"
                "</body></html>"
            ),
            media_type="text/html",
        )

    @app.post("/api/google/disconnect")
    def google_disconnect() -> dict[str, bool]:
        tokens = container.google.clear_tokens()
        if _google_oauth_configured():
            oauth, _scopes = _google_oauth()
            oauth.revoke(tokens.get("refresh_token") or tokens.get("access_token") or "")
        container.audit.record("google.disconnected", "dashboard", {})
        return {"disconnected": True}

    def _mcp_payload(server: Any) -> dict[str, Any]:
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
        }

    def _refresh_mcp_tools() -> int:
        registry = container.registry
        unregister = getattr(registry, "unregister_prefix", None)
        if callable(unregister):
            unregister("mcp:")
        count = 0
        for server in container.mcp_servers.list():
            if not server.enabled:
                continue
            specs = container.mcp_adapter.discover(server)
            registry.register_all(specs)
            count += len(specs)
        return count

    @app.get("/api/mcp/servers")
    def list_mcp_servers() -> list[dict[str, Any]]:
        return [_mcp_payload(row) for row in container.mcp_servers.list()]

    @app.post("/api/mcp/servers", status_code=201)
    def create_mcp_server(request: McpServerCreateRequest) -> dict[str, Any]:
        from personal_agent.domain.mcp import McpServer, McpTransport

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
        container.mcp_servers.save(server)
        tools = _refresh_mcp_tools()
        container.audit.record("mcp.server_created", "dashboard", {"id": server.id, "tools": tools})
        payload = _mcp_payload(server)
        payload["registered_tools"] = tools
        return payload

    @app.patch("/api/mcp/servers/{server_id}")
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
        container.mcp_servers.save(server)
        tools = _refresh_mcp_tools()
        payload = _mcp_payload(server)
        payload["registered_tools"] = tools
        return payload

    @app.delete("/api/mcp/servers/{server_id}", status_code=204)
    def delete_mcp_server(server_id: str) -> Response:
        if container.mcp_servers.get(server_id) is None:
            raise HTTPException(status_code=404, detail="MCP server not found.")
        container.mcp_servers.delete(server_id)
        _refresh_mcp_tools()
        return Response(status_code=204)

    @app.post("/api/mcp/servers/{server_id}/discover")
    def discover_mcp_server(server_id: str) -> dict[str, Any]:
        server = container.mcp_servers.get(server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found.")
        specs = container.mcp_adapter.discover(server)
        tools = _refresh_mcp_tools()
        return {
            "server_id": server_id,
            "discovered": [{"name": spec.name, "access_kind": spec.access_kind} for spec in specs],
            "registered_tools": tools,
        }

    @app.get("/api/google/gmail")
    def google_gmail(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=8, ge=1, le=50),
    ) -> dict[str, Any]:
        from personal_agent.infrastructure.integrations.google.clients import (
            GoogleApiClient,
            GoogleApiError,
        )

        client = GoogleApiClient(access_token_provider=_google_access_token)
        try:
            return client.list_gmail(page=page, page_size=page_size)
        except GoogleApiError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/api/google/calendar")
    def google_calendar(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=8, ge=1, le=50),
    ) -> dict[str, Any]:
        from personal_agent.infrastructure.integrations.google.clients import (
            GoogleApiClient,
            GoogleApiError,
        )

        client = GoogleApiClient(access_token_provider=_google_access_token)
        try:
            return client.list_calendar(page=page, page_size=page_size)
        except GoogleApiError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/api/google/drive")
    def google_drive(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=8, ge=1, le=50),
    ) -> dict[str, Any]:
        from personal_agent.infrastructure.integrations.google.clients import (
            GoogleApiClient,
            GoogleApiError,
        )

        client = GoogleApiClient(access_token_provider=_google_access_token)
        try:
            return client.list_drive(page=page, page_size=page_size)
        except GoogleApiError as exc:
            raise HTTPException(502, str(exc)) from exc

    # Outermost so preflights and auth error JSON still get CORS headers for Vercel.
    cors_origins = sorted(_configured_frontend_origins(settings))
    if production and cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_origin_regex=r"https://personal-ai-agent[\w-]*\.vercel\.app",
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )

    return app


# Vercel deployment + stable aliases for this project (preview hashes change per deploy).
_VERCEL_PROJECT_ORIGIN = re.compile(r"^https://personal-ai-agent[\w-]*\.vercel\.app$")


def _configured_frontend_origins(settings: Settings) -> set[str]:
    """Parse FRONTEND_ORIGIN as a single origin or comma-separated list."""
    origins: set[str] = set()
    raw = (settings.frontend_origin or "").strip()
    if not raw:
        return origins
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if origin:
            origins.add(origin)
    return origins


def _allowed_browser_origins(settings: Settings) -> set[str]:
    """Origins allowed to call the dashboard API from a browser."""
    origins = {
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    }
    origins.update(_configured_frontend_origins(settings))
    return origins


def _origin_allowed(origin: str, allowed: set[str], *, production: bool) -> bool:
    """Exact allow-list match, plus Vercel project URLs in production."""
    if origin in allowed:
        return True
    return bool(production and _VERCEL_PROJECT_ORIGIN.fullmatch(origin))


def _create_dashboard_session(secret_key: str) -> str:
    issued_at = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    payload = f"{issued_at}.{nonce}"
    signature = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload}.{encoded_signature}"


def _valid_dashboard_session(request: Request, secret_key: str) -> bool:
    token = request.cookies.get("personal_agent_session", "")
    try:
        issued_text, nonce, supplied_text = token.split(".", maxsplit=2)
        issued_at = int(issued_text)
        supplied = base64.urlsafe_b64decode(supplied_text + "=" * (-len(supplied_text) % 4))
    except (ValueError, TypeError):
        return False
    now = int(time.time())
    if issued_at > now or now - issued_at > 12 * 60 * 60:
        return False
    expected = hmac.new(
        secret_key.encode(), f"{issued_text}.{nonce}".encode(), hashlib.sha256
    ).digest()
    return secrets.compare_digest(expected, supplied)


_FOREIGN_TELEGRAM_PHASES = frozenset({"starting", "polling", "responding", "error"})


def telegram_foreign_runtime_active(container: AppContainer, worker: object | None) -> bool:
    """True when audit shows a non-dashboard bot polling and this worker is not running."""
    if worker is None:
        return False
    runtime = _telegram_runtime(container)["runtime"]
    return runtime in _FOREIGN_TELEGRAM_PHASES and not bool(getattr(worker, "running", False))


def _telegram_runtime(container: AppContainer) -> dict[str, Any]:
    events = container.audit.list_recent(limit=1, events=["telegram.runtime"])
    if not events:
        return {"runtime": "unknown", "last_seen": None, "username": None}
    event = events[0]
    occurred = datetime.fromisoformat(event["occurred_at"])
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=UTC)
    phase = event["details"].get("phase", "unknown")
    threshold = container.settings.ollama_timeout_seconds + 60 if phase == "responding" else 90
    stale = (datetime.now(UTC) - occurred).total_seconds() > threshold
    runtime = "stopped" if phase == "stopped" else ("stale" if stale else phase)
    return {
        "runtime": runtime,
        "last_seen": occurred.isoformat(),
        "username": event["details"].get("username"),
        "error_type": event["details"].get("error_type"),
    }
