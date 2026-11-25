"""Shared dashboard API helpers (Phase 6 router split)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from personal_agent.app.container import AppContainer
from personal_agent.application.inbox_items import approval_payload
from personal_agent.application.task_payloads import task_payload  # noqa: F401  (re-export)
from personal_agent.domain.approvals import Approval
from personal_agent.domain.models import AgentRun, OwnerProfile, RunEvent, RunStep

DASHBOARD_OWNER = "dashboard"

_FOREIGN_TELEGRAM_PHASES = frozenset({"starting", "polling", "responding", "error"})


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def run_payload(run: AgentRun) -> dict[str, Any]:
    latency_ms: int | None = None
    if run.created_at is not None and run.finished_at is not None:
        latency_ms = int((run.finished_at - run.created_at).total_seconds() * 1000)
    return {
        "id": run.id,
        "session_id": run.session_id,
        "origin": run.origin,
        "status": run.status.value,
        "prompt_version": run.prompt_version,
        "model": run.model,
        "trace_id": run.trace_id or "",
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "latency_ms": latency_ms,
        "input": run.input_text,
        "reply": run.final_text,
        "error": run.error,
        "stop_reason": run.stop_reason,
        "created_at": iso(run.created_at),
        "finished_at": iso(run.finished_at),
    }


def step_payload(step: RunStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "seq": step.seq,
        "kind": step.kind,
        "name": step.name,
        "status": step.status.value,
        "arguments": step.arguments,
        "output": step.output,
        "error": step.error,
        "result_type": step.result_type or "generic",
        "result_json": dict(step.result_json or {}),
        "started_at": iso(step.started_at),
        "finished_at": iso(step.finished_at),
        "duration_ms": step.duration_ms,
    }


def event_line(event: RunEvent) -> str:
    return (
        json.dumps(
            {"seq": event.seq, "run_id": event.run_id, "type": event.type, "data": event.data},
            ensure_ascii=False,
            default=str,
        )
        + "\n"
    )


def approval_payload_row(approval: Approval, now: datetime | None = None) -> dict[str, Any]:
    return approval_payload(approval, now)


def profile_payload(
    profile: OwnerProfile,
    *,
    email: str = "",
    has_photo: bool = False,
    member_since: datetime | None = None,
) -> dict[str, Any]:
    return {
        "name": profile.name,
        "email": email,
        "timezone": profile.timezone,
        "language": profile.language,
        "wizard_completed": profile.wizard_completed,
        "bio": profile.bio,
        "birthday": profile.birthday,
        "has_photo": has_photo,
        "photo_url": "/api/profile/photo" if has_photo else None,
        "member_since": iso(member_since or profile.created_at),
    }


def create_dashboard_session(secret_key: str) -> str:
    issued_at = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    payload = f"{issued_at}.{nonce}"
    signature = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload}.{encoded_signature}"


def valid_dashboard_session(request: Request, secret_key: str) -> bool:
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


def telegram_foreign_runtime_active(container: AppContainer, worker: object | None) -> bool:
    """True when audit shows a non-dashboard bot polling and this worker is not running."""
    if worker is None:
        return False
    runtime = telegram_runtime(container)["runtime"]
    return runtime in _FOREIGN_TELEGRAM_PHASES and not bool(getattr(worker, "running", False))


def telegram_runtime(container: AppContainer) -> dict[str, Any]:
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
