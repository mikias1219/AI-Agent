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
    ("day_", "tasks"),
    ("drive_", "google"),
    ("reminder_", "reminders"),
    ("memory_", "memory"),
    ("goal_", "goals"),
    ("habit_", "life"),
    ("finance_", "finance"),
    ("plan_", "goals"),
    ("note_", "life"),
    ("diary_", "life"),
    ("file_", "life"),
    ("learn_", "life"),
    ("reading_", "life"),
    ("google_", "google"),
    ("web_", "web"),
    ("telegram_", "telegram"),
    ("mcp_", "mcp"),
)

# Always offered, whatever the router or a skill picks, so core life tools never vanish.
ALWAYS_GROUPS = frozenset({"core", "tasks", "life", "goals"})

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


def _latest_user_text(history: Sequence[Message]) -> str:
    for message in reversed(history):
        if message.role == "user" and message.content:
            return message.content[:2000]
    return ""


def select_tools(
    history: Sequence[Message],
    tools: Sequence[ToolSpec],
    *,
    connected: frozenset[str] | None = None,
    router: ModelRouter | None = None,
    skill_groups: frozenset[str] | None = None,
) -> list[ToolSpec]:
    """Return tools for connected integrations (+ core). Compact via skill or fast model."""
    request = _latest_user_text(history)
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
                "life",
                "finance",
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
    if skill_groups:
        # Skill groups are a priority, not a filter: daily-life reads stay available.
        narrowed = frozenset(skill_groups) | ALWAYS_GROUPS
        skill_eligible = [tool for tool in eligible if integration_group(tool) in narrowed]
        if skill_eligible:
            return skill_eligible
    if len(eligible) <= COMPACT_LIMIT or router is None:
        return eligible

    groups = sorted({integration_group(tool) for tool in eligible})
    try:
        chosen = router.choose_tool_groups(groups, request)
    except Exception:  # noqa: BLE001 — fall back to full eligible set
        logger.warning("Fast tool-group routing failed; using full eligible set")
        return eligible
    chosen_set = frozenset(chosen) | ALWAYS_GROUPS
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
