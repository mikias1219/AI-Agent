"""Chat, runs and conversations (Phase 6 split)."""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer
from personal_agent.domain.approvals import ApprovalStatus
from personal_agent.domain.exceptions import AgentError, StorageError
from personal_agent.domain.models import AgentRun, RunStatus
from personal_agent.presentation.web.routers._common import (
    DASHBOARD_OWNER,
    approval_payload_row,
    event_line,
    run_payload,
    step_payload,
)

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    session_id: str | None = None


class RunStartRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    session_id: str | None = None


def build_runs_chat_router(
    container: AppContainer,
    *,
    enforce_api_rate_limit: Callable[[Request], None],
) -> APIRouter:
    router = APIRouter(tags=["runs", "chat"])

    def own_run(run_id: str) -> AgentRun:
        try:
            run = container.runs.get(run_id)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail="Run not found.") from exc
        if run.user_id != DASHBOARD_OWNER:
            raise HTTPException(status_code=404, detail="Run not found.")
        return run

    @router.post("/api/chat")
    def chat(http_request: Request, request: ChatRequest) -> dict[str, str]:
        enforce_api_rate_limit(http_request)
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

    @router.post("/api/chat/stream")
    def stream_chat(http_request: Request, request: ChatRequest) -> StreamingResponse:
        enforce_api_rate_limit(http_request)
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

    @router.post("/api/runs", status_code=202)
    def start_run(http_request: Request, request: RunStartRequest) -> dict[str, Any]:
        enforce_api_rate_limit(http_request)
        live = [
            r
            for r in container.runs.list_recent(DASHBOARD_OWNER, limit=10)
            if r.status.value in {"running", "awaiting_approval"}
        ]
        if len(live) >= container.settings.max_concurrent_runs:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Already {len(live)} runs in progress "
                    f"(limit {container.settings.max_concurrent_runs}). "
                    "Wait for one to finish or stop it."
                ),
            )
        try:
            run = container.runs.start(
                user_id=DASHBOARD_OWNER,
                text=request.text,
                session_id=request.session_id,
                origin="dashboard",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return run_payload(run)

    @router.get("/api/runs/active")
    def active_run() -> dict[str, Any] | None:
        run = container.runs.active(DASHBOARD_OWNER)
        return run_payload(run) if run else None

    @router.get("/api/runs")
    def list_runs(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return [
            run_payload(run) for run in container.runs.list_recent(DASHBOARD_OWNER, limit=limit)
        ]

    @router.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        run = own_run(run_id)
        steps = container.runs.steps(run.id)
        return {
            **run_payload(run),
            "steps": [step_payload(step) for step in steps],
            "approvals": [
                approval_payload_row(item) for item in container.approval_service.for_run(run.id)
            ],
        }

    @router.get("/api/runs/{run_id}/events")
    def run_events(run_id: str, after: int = Query(default=0, ge=0)) -> StreamingResponse:
        own_run(run_id)

        def body():
            for event in container.runs.events(run_id, after_seq=after):
                yield "\n" if event is None else event_line(event)

        return StreamingResponse(
            body(),
            media_type="application/x-ndjson",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
        )

    @router.post("/api/runs/{run_id}/cancel", status_code=202)
    def cancel_run(run_id: str) -> dict[str, Any]:
        run = own_run(run_id)
        if run.status is RunStatus.AWAITING_APPROVAL:
            for item in container.approval_service.for_run(run_id):
                if item.status is ApprovalStatus.PENDING:
                    container.approval_service.decide(
                        item.id, False, actor=DASHBOARD_OWNER, channel="dashboard"
                    )
            return run_payload(own_run(run_id))
        return run_payload(container.runs.cancel(run_id))

    @router.get("/api/conversations")
    def conversations(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return [
            {
                "id": item.id,
                "user_id": item.user_id,
                "created_at": item.created_at.isoformat(),
            }
            for item in container.conversations.list_sessions(limit=limit)
        ]

    @router.get("/api/conversations/{session_id}/messages")
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

    return router