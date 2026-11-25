"""Loopback-only web dashboard for chat and local agent operations."""

from __future__ import annotations

import asyncio
import logging
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from personal_agent.app.container import AppContainer, build_app
from personal_agent.application.security.login_lockout import LoginLockoutStore
from personal_agent.application.security.oauth_state import UsedStates
from personal_agent.application.security.rate_limit import SlidingWindowRateLimiter
from personal_agent.config.settings import Settings, load_settings
from personal_agent.domain.exceptions import ConfigurationError
from personal_agent.domain.life import LifeError
from personal_agent.infrastructure.integrations.telegram.runner import build_allowed_chats
from personal_agent.infrastructure.model_providers.runtime_selection import (
    hermes_installed,
    probe_ollama_reachable,
)
from personal_agent.presentation.web.routers._common import (
    DASHBOARD_OWNER,
    telegram_foreign_runtime_active,
    valid_dashboard_session,
)

logger = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).resolve().parents[5] / "frontend" / "dist"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})


def should_autostart_telegram(worker: object | None, allowed: frozenset[int]) -> bool:
    """Start the dashboard-owned worker when token wiring exists and chats are allowlisted."""
    return worker is not None and bool(allowed)


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

    @app.exception_handler(LifeError)
    async def life_error_handler(_request: Request, exc: LifeError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    app.state.login_lockout = LoginLockoutStore(Path("data") / "login_lockout.json")
    app.state.api_rate_limiter = SlidingWindowRateLimiter(limit=settings.api_rate_limit_per_minute)
    app.state.google_oauth_states = UsedStates()
    production = settings.environment == "production"
    cookie_secure = production
    cookie_samesite = "lax" if production else "strict"
    allowed_origins = _allowed_browser_origins(settings)

    _RATE_LIMITED_PREFIXES = (
        "/api/chat",
        "/api/runs",
        "/api/mcp",
    )

    def _enforce_api_rate_limit(request: Request) -> None:
        path = request.url.path
        limited = any(
            path == prefix or path.startswith(prefix + "/") for prefix in _RATE_LIMITED_PREFIXES
        )
        if not limited:
            return
        client = request.client.host if request.client else "unknown"
        key = f"{DASHBOARD_OWNER}:{client}:{path.split('/')[2]}"
        if not app.state.api_rate_limiter.allow(key):
            raise HTTPException(status_code=429, detail="Too many requests. Try again shortly.")

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
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        response: Response
        public = path in {
            "/",
            "/login",
            "/demo",
            "/api/login",
            "/api/register",
            "/api/auth",
            "/api/health",
            "/api/google/callback",
            "/internal/tick",
            "/internal/demo/reset",
        }
        public = (
            public
            or path.startswith("/assets/")
            or path.startswith("/api/demo/")
            or path.startswith("/demo/")
        )
        if not public and not valid_dashboard_session(request, session_key()):
            response = JSONResponse({"detail": "Login required."}, 401)
        else:
            response = await call_next(request)
        if (path.startswith("/api/") or path in {"/", "/login"}) and (
            "cache-control" not in response.headers
        ):
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
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
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

    @app.get("/demo", include_in_schema=False)
    @app.get("/demo/{rest:path}", include_in_schema=False)
    def demo_page(rest: str = "") -> FileResponse:
        return index()

    @app.get("/api/health")
    def health(request: Request) -> dict[str, Any]:
        """Public: liveness only (S9). Authenticated session gets full probe details."""
        if not valid_dashboard_session(request, session_key()):
            return {"status": "ok"}

        from personal_agent.infrastructure.observability.health import build_health_payload

        current = container.settings
        database_url = current.database_url.lower()
        if "postgres" in database_url:
            storage = "postgres"
        elif database_url.startswith("sqlite"):
            storage = "sqlite"
        else:
            storage = "other"
        installed = hermes_installed(current.hermes_directory)
        ollama_ok = probe_ollama_reachable(current.ollama_base_url)
        base = {
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
            "ollama_reachable": ollama_ok,
            "frontend_origin_configured": bool(current.frontend_origin),
            "trace_exporter": current.trace_exporter,
        }
        worker = container.telegram_worker

        def _db_ping() -> None:
            container.runs_repository.list_recent(limit=1)

        return build_health_payload(
            base=base,
            database_ping=_db_ping,
            audit_list=container.audit.list_recent,
            provider=current.provider,
            ollama_reachable=ollama_ok,
            openai_key_present=bool(current.openai_compat_api_key),
            telegram_worker_running=bool(worker and worker.running),
        )

    from personal_agent.presentation.web.demo_routes import (
        build_demo_router,
        build_internal_demo_router,
    )
    from personal_agent.presentation.web.routers.agent import build_agent_router
    from personal_agent.presentation.web.routers.auth import build_auth_router
    from personal_agent.presentation.web.routers.days import build_days_router
    from personal_agent.presentation.web.routers.goals import build_goals_router
    from personal_agent.presentation.web.routers.google import build_google_router
    from personal_agent.presentation.web.routers.integrations import build_integrations_router
    from personal_agent.presentation.web.routers.life import build_life_router
    from personal_agent.presentation.web.routers.memory import build_memory_router
    from personal_agent.presentation.web.routers.profile import build_profile_router
    from personal_agent.presentation.web.routers.runs_chat import build_runs_chat_router
    from personal_agent.presentation.web.routers.sync import build_sync_router
    from personal_agent.presentation.web.routers.tasks import build_tasks_router
    from personal_agent.presentation.web.routers.today_inbox import build_today_inbox_router
    from personal_agent.presentation.web.routers.workspace import build_workspace_router

    app.include_router(build_agent_router(container))
    app.include_router(build_workspace_router(container))
    app.include_router(
        build_auth_router(
            container,
            session_key=session_key,
            cookie_secure=cookie_secure,
            cookie_samesite=cookie_samesite,
        )
    )
    app.include_router(build_tasks_router(container))
    app.include_router(build_goals_router(container))
    app.include_router(build_life_router(container))
    app.include_router(build_days_router(container))
    app.include_router(build_sync_router(container))
    app.include_router(build_profile_router(container))
    app.include_router(
        build_runs_chat_router(container, enforce_api_rate_limit=_enforce_api_rate_limit)
    )
    app.include_router(build_google_router(container, session_key=session_key))
    app.include_router(
        build_integrations_router(
            container,
            production=production,
            enforce_api_rate_limit=_enforce_api_rate_limit,
        )
    )
    app.include_router(build_memory_router(container))
    app.include_router(build_today_inbox_router(container))
    app.include_router(build_demo_router())
    app.include_router(build_internal_demo_router())

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
