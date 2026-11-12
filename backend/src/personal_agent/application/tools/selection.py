"""Select tools by integration group — never by English keyword heuristics (AGT-06).

Connected integrations plus core are always eligible. When more than COMPACT_LIMIT
tools remain, optionally ask the fast model for a compact group subset.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from personal_agent.domain.models import Message, ToolSpec

if TYPE_CHECKING:
    from personal_agent.application.model_router import ModelRouter

logger = logging.getLogger(__name__)

COMPACT_LIMIT = 12

# name prefix / exact → integration group
_GROUP_PREFIXES: tuple[tuple[str, str], ...] = (
    ("task_", "tasks"),
    ("reminder_", "reminders"),
    ("memory_", "memory"),
    ("goal_", "goals"),
    ("plan_", "goals"),
    ("google_", "google"),
    ("web_", "web"),
    ("telegram_", "telegram"),
    ("mcp_", "mcp"),
)

CORE_TOOLS = frozenset({"get_current_datetime", "noop"})


def integration_group(spec: ToolSpec) -> str:
    if spec.integration:
        return spec.integration
    if spec.name in CORE_TOOLS:
        return "core"
    for prefix, group in _GROUP_PREFIXES:
        if spec.name.startswith(prefix):
            return group
    return "core"


def select_tools(
    history: Sequence[Message],
    tools: Sequence[ToolSpec],
    *,
    connected: frozenset[str] | None = None,
    router: ModelRouter | None = None,
) -> list[ToolSpec]:
    """Return tools for connected integrations (+ core). Compact via fast model when large."""
    del history  # reserved for future context-aware routing without English regex
    allowed = (
        connected
        if connected is not None
        else frozenset(
            {
                "core",
                "tasks",
                "reminders",
                "memory",
                "goals",
                "google",
                "web",
                "telegram",
                "mcp",
            }
        )
    )
    eligible = [
        tool
        for tool in tools
        if integration_group(tool) == "core" or integration_group(tool) in allowed
    ]
    if len(eligible) <= COMPACT_LIMIT or router is None:
        return eligible

    groups = sorted({integration_group(tool) for tool in eligible})
    try:
        chosen = router.choose_tool_groups(groups)
    except Exception:  # noqa: BLE001 — fall back to full eligible set
        logger.warning("Fast tool-group routing failed; using full eligible set")
        return eligible
    chosen_set = frozenset(chosen) | frozenset({"core"})
    compacted = [tool for tool in eligible if integration_group(tool) in chosen_set]
    return compacted or eligible


def parse_group_list(raw: str, available: Sequence[str]) -> list[str]:
    """Parse model JSON/list output into known group names."""
    text = (raw or "").strip()
    available_set = set(available)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and "groups" in data:
        data = data["groups"]
    if isinstance(data, list):
        return [str(item) for item in data if str(item) in available_set]
    # bare tokens
    tokens = [t.strip(" ,[]\"'") for t in text.replace("\n", " ").split()]
    return [t for t in tokens if t in available_set]
