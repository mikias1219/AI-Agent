"""Shared pieces of the Drive and Calendar sync services (contract sections 8-9).

Both syncs write to the owner's Google account, so both go through `ToolRegistry.execute`
like any other commit action. The registry decides: with mode `ask` it records ONE durable
approval for the whole batch (the owner's consent for exactly those objects); with mode
`auto` (the owner set the tool to Allow) it runs at once. Pause, policy ceilings and the daily
commit budget are the registry's, not ours.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from personal_agent.domain.exceptions import (
    AgentError,
    ApprovalPendingError,
)
from personal_agent.domain.life import LifeConflict, LifeError
from personal_agent.domain.models import ToolCall, ToolContext
from personal_agent.domain.ports import ToolRegistry

CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"
READ_ONLY_MESSAGE = "Google is in Read-only mode. Turn off Read-only under Connections first."


class SyncUnavailable(LifeConflict):
    """Google is not connected, a scope is missing or writes are blocked (409)."""


class SyncFailed(LifeError):
    """The batch ran and failed as a whole (502)."""

    status_code = 502


def scope_granted(status: Mapping[str, Any], scope: str) -> bool:
    if not status.get("connected"):
        return False
    return scope in str(status.get("scopes") or "").split()


def mode_label(approval_required: bool) -> str:
    return "ask" if approval_required else "auto"


def run_batch(
    registry: ToolRegistry,
    *,
    owner: str,
    origin: str,
    session: str,
    tool: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Request the batch through the registry. Returns the response shape of `/run`."""
    ctx = ToolContext(user_id=owner, session_id=session, origin=origin)
    call = ToolCall(id=uuid.uuid4().hex, name=tool, arguments=arguments)
    try:
        result = registry.execute(call, ctx)
    except ApprovalPendingError as exc:
        return {"status": "awaiting_approval", "approval_id": exc.approval_id, "summary": None}
    except AgentError as exc:
        raise SyncUnavailable(str(exc)) from exc
    if not result.ok:
        raise SyncFailed(result.error or "The sync did not complete.")
    try:
        parsed = json.loads(result.output)
    except json.JSONDecodeError:
        parsed = {}
    summary = {
        key: int(parsed.get(key) or 0) for key in ("created", "updated", "skipped", "failed")
    }
    return {"status": "done", "approval_id": None, "summary": summary}


Handler = Callable[[ToolContext, Mapping[str, Any]], str]
