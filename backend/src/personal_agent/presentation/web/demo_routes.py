"""Public demo API under /api/demo/* (UX-12). Isolated from the owner workspace."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer, get_demo_app, reset_app
from personal_agent.application.demo.seed import DEMO_OWNER, ensure_demo_seeded, reset_demo_database
from personal_agent.domain.models import AgentRun, RunStep

_rate_lock = threading.Lock()
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


class DemoChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=64)


class DemoTaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


def _client_key(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host or "unknown"


def enforce_demo_rate_limit(request: Request, per_minute: int) -> None:
    now = time.monotonic()
    key = _client_key(request)
    with _rate_lock:
        bucket = _rate_buckets[key]
        while bucket and now - bucket[0] > 60.0:
            bucket.popleft()
        if len(bucket) >= per_minute:
            raise HTTPException(
                status_code=429, detail="Demo rate limit exceeded. Try again shortly."
            )
        bucket.append(now)


def _iso(value: object) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _run_payload(run: AgentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "session_id": run.session_id,
        "origin": run.origin,
        "status": run.status.value,
        "model": run.model,
        "trace_id": run.trace_id or "",
        "input": run.input_text,
        "reply": run.final_text,
        "error": run.error,
        "stop_reason": run.stop_reason,
        "created_at": _iso(run.created_at),
        "finished_at": _iso(run.finished_at),
        "demo": True,
    }


def _step_payload(step: RunStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "seq": step.seq,
        "kind": step.kind,
        "name": step.name,
        "status": step.status.value,
        "output": step.output,
        "error": step.error,
        "duration_ms": step.duration_ms,
    }


def build_demo_router() -> APIRouter:
    router = APIRouter(prefix="/api/demo", tags=["demo"])

    def demo() -> AppContainer:
        return get_demo_app()

    @router.get("/health")
    def demo_health(request: Request) -> dict[str, Any]:
        container = demo()
        enforce_demo_rate_limit(request, container.settings.demo_rate_limit_per_minute)
        return {
            "status": "ok",
            "demo": True,
            "banner": "Simulated workspace — external actions are labeled SIMULATED.",
            "owner": DEMO_OWNER,
            "provider": "fake",
        }

    @router.post("/session")
    def demo_session(request: Request) -> dict[str, Any]:
        container = demo()
        enforce_demo_rate_limit(request, container.settings.demo_rate_limit_per_minute)
        summary = ensure_demo_seeded(container)
        tasks = container.tasks.list(owner_user_id=DEMO_OWNER)
        memories = container.memories.list(DEMO_OWNER, limit=20)
        return {
            "demo": True,
            "owner": DEMO_OWNER,
            "seed": summary,
            "tasks": [{"id": t.id, "title": t.title, "status": t.status.value} for t in tasks[:20]],
            "memories": [{"id": m.id, "kind": m.kind, "content": m.content} for m in memories[:20]],
            "banner": (
                "You are in demo mode. Data resets nightly and never mixes with real accounts."
            ),
        }

    @router.post("/chat")
    def demo_chat(body: DemoChatRequest, request: Request) -> dict[str, Any]:
        container = demo()
        enforce_demo_rate_limit(request, container.settings.demo_rate_limit_per_minute)
        session_id, reply = container.chat.turn(
            user_id=DEMO_OWNER,
            session_id=body.session_id,
            text=body.text,
            origin="demo",
        )
        return {"session_id": session_id, "reply": reply, "demo": True}

    @router.get("/tasks")
    def demo_tasks(request: Request) -> list[dict[str, Any]]:
        container = demo()
        enforce_demo_rate_limit(request, container.settings.demo_rate_limit_per_minute)
        return [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value,
                "created_at": _iso(t.created_at),
            }
            for t in container.tasks.list(owner_user_id=DEMO_OWNER)
        ]

    @router.post("/tasks", status_code=201)
    def demo_create_task(body: DemoTaskCreateRequest, request: Request) -> dict[str, Any]:
        container = demo()
        enforce_demo_rate_limit(request, container.settings.demo_rate_limit_per_minute)
        task_id = container.tasks.create(title=body.title, owner_user_id=DEMO_OWNER)
        task = container.tasks.get(task_id)
        assert task is not None
        return {"id": task.id, "title": task.title, "status": task.status.value, "demo": True}

    @router.get("/activity")
    def demo_activity(
        request: Request,
        limit: int = Query(default=50, ge=1, le=200),
        origin: str | None = Query(default=None),
        event: str | None = Query(default=None),
    ) -> list[dict[str, Any]]:
        container = demo()
        enforce_demo_rate_limit(request, container.settings.demo_rate_limit_per_minute)
        rows = container.audit.list_recent(limit=limit, offset=0)
        if event:
            rows = [r for r in rows if r.get("event") == event]
        if origin:
            rows = [
                r
                for r in rows
                if isinstance(r.get("details"), dict)
                and str((r.get("details") or {}).get("origin") or "") == origin
            ]
        return rows

    @router.get("/runs/{run_id}")
    def demo_run(run_id: str, request: Request) -> dict[str, Any]:
        container = demo()
        enforce_demo_rate_limit(request, container.settings.demo_rate_limit_per_minute)
        run = container.runs_repository.get(run_id)
        if run is None or run.user_id != DEMO_OWNER:
            raise HTTPException(status_code=404, detail="Run not found.")
        steps = container.runs_repository.list_steps(run.id)
        return {**_run_payload(run), "steps": [_step_payload(s) for s in steps]}

    @router.post("/reset")
    def demo_reset(request: Request) -> dict[str, Any]:
        """Public soft reset for the demo (also used by nightly job via /internal/demo/reset)."""
        container = demo()
        enforce_demo_rate_limit(request, max(5, container.settings.demo_rate_limit_per_minute // 4))
        url = container.settings.demo_database_url
        reset_demo_database(url)
        reset_app()
        fresh = get_demo_app(force_rebuild=True)
        summary = ensure_demo_seeded(fresh, force=True)
        return {"reset": True, "seed": summary}

    return router


def build_internal_demo_router() -> APIRouter:
    router = APIRouter(tags=["demo-internal"])

    @router.post("/internal/demo/reset")
    def internal_demo_reset(request: Request) -> dict[str, Any]:
        from personal_agent.app.container import get_app

        owner = get_app()
        expected = owner.settings.internal_tick_secret or owner.settings.dashboard_secret_key
        provided = request.headers.get("X-Aura-Tick-Secret", "")
        if not expected or provided != expected:
            raise HTTPException(status_code=401, detail="Invalid reset secret.")
        reset_demo_database(owner.settings.demo_database_url)
        reset_app()
        fresh = get_demo_app(force_rebuild=True)
        return {"reset": True, "seed": ensure_demo_seeded(fresh, force=True)}

    return router
