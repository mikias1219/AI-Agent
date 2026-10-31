"""Loopback-only web dashboard for chat and local agent operations."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import queue
import secrets
import threading
import time
from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer, build_app
from personal_agent.config.settings import Settings, load_settings
from personal_agent.domain.exceptions import AgentError, ConfigurationError, StorageError
from personal_agent.domain.models import Task, TaskStatus
from personal_agent.infrastructure.integrations.telegram.runner import build_allowed_chats

logger = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).resolve().parents[5] / "frontend" / "dist"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    session_id: str | None = None


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=10_000)


class TaskStatusRequest(BaseModel):
    status: TaskStatus


class ApprovalDecisionRequest(BaseModel):
    approve: bool


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)
    email: str = Field(default="", max_length=254)


class RegistrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=1024)


class DashboardApprovalNotifier:
    """Wait for a dashboard decision while a live tool request is awaiting approval."""

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout_seconds = max(0.0, timeout_seconds)
        self._lock = threading.Lock()
        self._waiting: dict[str, tuple[threading.Event, str | None]] = {}
        self._decide: Callable[[str, bool], None] | None = None

    def bind_decider(self, decide: Callable[[str, bool], None]) -> None:
        self._decide = decide

    def __call__(self, _prompt: str, details: Mapping[str, Any]) -> str:
        approval_id = str(details["approval_id"])
        event = threading.Event()
        with self._lock:
            self._waiting[approval_id] = (event, None)

        event.wait(self._timeout_seconds)
        with self._lock:
            _, decision = self._waiting.pop(approval_id, (event, None))
        return decision or "deferred"

    def is_waiting(self, approval_id: str) -> bool:
        with self._lock:
            return approval_id in self._waiting

    def resolve(self, approval_id: str, approve: bool) -> str:
        with self._lock:
            pending = self._waiting.get(approval_id)
            if pending is None:
                raise StorageError("This approval is no longer waiting for a dashboard decision.")
            if self._decide is None:
                raise RuntimeError("Approval gateway was not connected to the dashboard.")
            self._decide(approval_id, approve)
            decision = "approved" if approve else "denied"
            self._waiting[approval_id] = (pending[0], decision)
            pending[0].set()
            return decision


def _task_payload(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "owner_user_id": task.owner_user_id,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def create_dashboard_app(
    *,
    container: AppContainer | None = None,
    settings: Settings | None = None,
    approval_notifier: DashboardApprovalNotifier | None = None,
    frontend_dir: Path | None = None,
) -> FastAPI:
    """Create the dashboard API and page; the CLI binds its server to loopback only."""
    settings = settings or (container.settings if container else load_settings())
    if len(settings.dashboard_secret_key) < 32:
        raise ConfigurationError(
            "Run personal-agent init-dashboard from backend/ before starting the dashboard."
        )
    notifier = approval_notifier or DashboardApprovalNotifier(settings.approval_timeout_seconds)
    container = container or build_app(settings=settings, approval_notifier=notifier)
    notifier.bind_decider(container.approvals.decide)

    frontend_dir = frontend_dir or FRONTEND_DIR
    react_index = frontend_dir / "index.html"

    def session_key() -> str:
        return container.auth.session_key(settings.dashboard_secret_key)

    @asynccontextmanager
    async def lifespan(_app):
        yield
        if container.telegram_worker:
            await asyncio.to_thread(container.telegram_worker.close)

    app = FastAPI(
        title="Personal Agent Dashboard", docs_url=None, redoc_url=None, lifespan=lifespan
    )
    app.state.container = container
    app.state.approval_notifier = notifier
    app.state.login_failures = {}
    app.state.login_lock = threading.Lock()

    @app.middleware("http")
    async def restrict_to_local_browser(request, call_next):  # noqa: ANN001
        host_header = request.headers.get("host", "")
        host = urlsplit(f"//{host_header}").hostname
        if host not in LOCAL_HOSTS:
            return JSONResponse({"detail": "Dashboard accepts local connections only."}, 400)
        origin = request.headers.get("origin")
        if origin:
            allowed_origins = {
                f"http://{host_header}",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            }
            if origin not in allowed_origins:
                return JSONResponse({"detail": "Cross-origin requests are not allowed."}, 403)
        path = request.url.path
        response: Response
        public = path in {"/", "/login", "/api/login", "/api/register", "/api/auth"}
        public = public or path.startswith("/assets/")
        if not public and not _valid_dashboard_session(request, session_key()):
            response = JSONResponse({"detail": "Login required."}, 401)
        else:
            response = await call_next(request)
        if path.startswith("/api/") or path in {"/", "/login"}:
            response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
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
            secure=False,
            samesite="strict",
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
        response.delete_cookie("personal_agent_session", path="/", httponly=True, samesite="strict")
        return response

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        current = container.settings
        return {
            "provider": current.provider,
            "model_setup": container.model_setup.read(),
            "model": (current.hermes_model or current.ollama_model)
            if current.provider == "hermes"
            else current.ollama_model
            if current.provider in ("ollama", "hermes")
            else "offline fake",
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
        return container.audit.list_recent(
            limit=limit,
            events=[
                "telegram.reply_sent",
                "telegram.reply_send_failed",
                "security.telegram_unauthorized_chat",
                "telegram.identity_verified",
            ],
        )

    @app.post("/api/telegram/start")
    def start_telegram():
        worker = container.telegram_worker
        if worker is None:
            raise HTTPException(400, "Configure TELEGRAM_BOT_TOKEN in backend/.env and restart.")
        runtime = _telegram_runtime(container)["runtime"]
        if runtime in {"starting", "polling", "responding", "error"} and not worker.running:
            raise HTTPException(409, "A bot is already active in another process. Stop it first.")
        worker.start()
        container.audit.record("telegram.start_requested", "dashboard", {})
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

    @app.get("/api/tasks")
    def tasks() -> list[dict[str, Any]]:
        return [_task_payload(task) for task in container.tasks.list()]

    @app.post("/api/tasks", status_code=201)
    def create_task(request: TaskCreateRequest) -> dict[str, Any]:
        try:
            task_id = container.tasks.create(
                title=request.title.strip(),
                description=request.description.strip(),
                owner_user_id="dashboard",
            )
            task = container.tasks.get(task_id)
        except (AgentError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if task is None:
            raise HTTPException(status_code=500, detail="Created task could not be reloaded.")
        return _task_payload(task)

    @app.patch("/api/tasks/{task_id}")
    def advance_task(task_id: str, request: TaskStatusRequest) -> dict[str, Any]:
        try:
            container.tasks.advance(task_id, request.status)
        except StorageError as exc:
            status_code = 404 if "unknown task" in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        except AgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        task = container.tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        return _task_payload(task)

    @app.get("/api/activity")
    def activity(
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, Any]]:
        return container.audit.list_recent(limit=limit, offset=offset)

    @app.get("/api/approvals")
    def approvals(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        items = container.approvals_repository.list_pending(limit=limit)
        for item in items:
            item["actionable"] = notifier.is_waiting(item["id"])
        return items

    @app.post("/api/approvals/{approval_id}/decision")
    def decide_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, str]:
        try:
            decision = notifier.resolve(approval_id, request.approve)
        except StorageError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"id": approval_id, "decision": decision}

    return app


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
