"""Builtin, risk-free tools: read-only, no credentials, no side effects.

Keep this module for genuinely useful basics. Anything touching email, files,
posts, or external accounts belongs in a future `integrations/`-backed tool module
with prepare→execute separation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from personal_agent.core.types import ToolContext
from personal_agent.tools.base import tool


@tool(
    "get_current_datetime",
    "Returns the current date and time as an ISO-8601 timestamp.",
    access_kind="read",
)
def get_current_datetime(_ctx: ToolContext, _args: dict[str, Any]) -> str:
    """UTC now, ISO formatted; timezone-aware so sorting is unambiguous."""
    return datetime.now(UTC).isoformat(timespec="seconds")


@tool(
    "noop",
    "Placeholder that does nothing; useful to smoke-test tool plumbing in dev.",
    access_kind="read",
)
def noop(_ctx: ToolContext, _args: dict[str, Any]) -> str:
    """Produces a fixed sentence without side effects."""
    return "noop ran successfully."
