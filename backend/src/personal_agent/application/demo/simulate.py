"""Mark execute/destructive demo tools as SIMULATED (UX-12)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from personal_agent.domain.models import ToolContext
from personal_agent.domain.ports import ToolRegistry


def wrap_tools_as_simulated(registry: ToolRegistry) -> int:
    """Replace execute/destructive handlers so they never touch external systems."""
    replaced = 0
    for spec in list(registry.specs()):
        if spec.access_kind not in ("execute", "destructive"):
            continue
        name = spec.name

        def handler(
            ctx: ToolContext,
            args: Mapping[str, object],
            *,
            _name: str = name,
        ) -> str:
            _ = ctx
            return (
                f"SIMULATED: {_name} was not sent to an external system. "
                f"Arguments: {dict(args)}"
            )

        updated = replace(
            spec,
            handler=handler,
            description=(spec.description or "") + " [SIMULATED in demo]",
        )
        if hasattr(registry, "replace"):
            registry.replace(updated)  # type: ignore[attr-defined]
        else:
            registry.register(updated)
        replaced += 1
    return replaced
