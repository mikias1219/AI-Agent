"""Agent control: autonomy preset, global pause and daily budgets (trust surface, A4 subset).

State lives on the owner profile (`agent_control_json`). `paused` is enforced by the tool
registry: while paused, only `read` tools run. Hard ceilings are never relaxed by a preset.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.domain.dates import get_zone

AUTONOMY_PRESETS = ("ask_first", "balanced", "proactive")
DEFAULT_PRESET = "ask_first"
DEFAULT_COMMITS_CAP = 10
DEFAULT_PROACTIVE_CAP = 3


@dataclass(slots=True)
class AgentControlState:
    autonomy_preset: str = DEFAULT_PRESET  # ask_first | balanced | proactive
    paused: bool = False
    budgets: dict[str, int] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "autonomy_preset": self.autonomy_preset,
            "paused": self.paused,
            "budgets": dict(self.budgets),
        }


class AgentControlService:
    """Read and update the owner's agent control state."""

    def __init__(
        self,
        profiles: ProfileService,
        *,
        commits_cap: int = DEFAULT_COMMITS_CAP,
        proactive_cap: int = DEFAULT_PROACTIVE_CAP,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._profiles = profiles
        self._commits_cap = commits_cap
        self._proactive_cap = proactive_cap
        self._clock = clock or (lambda: datetime.now(UTC))

    def get(self, owner_id: str) -> AgentControlState:
        profile = self._profiles.get(owner_id)
        return self._state(profile.agent_control, profile.timezone)

    def is_paused(self, owner_id: str) -> bool:
        return self.get(owner_id).paused

    def patch(
        self,
        owner_id: str,
        *,
        autonomy_preset: str | None = None,
        paused: bool | None = None,
    ) -> AgentControlState:
        if autonomy_preset is not None and autonomy_preset not in AUTONOMY_PRESETS:
            raise ValueError(
                f"Unknown autonomy preset '{autonomy_preset}'. Use one of: "
                f"{', '.join(AUTONOMY_PRESETS)}."
            )
        profile = self._profiles.get(owner_id)
        data = dict(profile.agent_control or {})
        if autonomy_preset is not None:
            data["autonomy_preset"] = autonomy_preset
        if paused is not None:
            data["paused"] = bool(paused)
        profile.agent_control = data
        self._profiles.save(profile)
        return self._state(data, profile.timezone)

    # -- internals -----------------------------------------------------------

    def _state(self, data: dict[str, Any], timezone: str) -> AgentControlState:
        preset = data.get("autonomy_preset")
        counters = data.get("counters") or {}
        local_day = self._clock().astimezone(get_zone(timezone)).date().isoformat()
        fresh = counters.get("date") == local_day  # daily counters reset by local date
        return AgentControlState(
            autonomy_preset=preset if preset in AUTONOMY_PRESETS else DEFAULT_PRESET,
            paused=bool(data.get("paused", False)),
            budgets={
                "commits_used": int(counters.get("commits_used", 0)) if fresh else 0,
                "commits_cap": self._commits_cap,
                "proactive_used": int(counters.get("proactive_used", 0)) if fresh else 0,
                "proactive_cap": self._proactive_cap,
            },
        )
