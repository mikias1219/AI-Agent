"""Per-tool Allow / Ask / Block policy backed by owner agent_control (APR-07).

Hard ceilings: email send / reply and destructive tools can never be set to Allow,
regardless of preset or stored preference (BR-05 and hard ceilings).

Balanced (AG-TRU-04): when the preset is Balanced and the owner has not explicitly
set Ask/Block for a reversible execute tool, that tool auto-runs with a 10-minute undo.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from personal_agent.domain.models import ToolContext, ToolSpec
from personal_agent.domain.undo import BALANCED_AUTO_EXECUTE

PermissionMode = str  # allow | ask | block

# Tools that may never auto-run, even if the owner picks Allow.
HARD_CEILING_TOOLS: frozenset[str] = frozenset(
    {
        "google_gmail_send",
        "google_gmail_reply",
        "telegram_send_message",
        "memory_forget_all",
    }
)


class OwnerPermissionPolicy:
    """Registry policy that reads live per-tool modes from agent control."""

    def __init__(
        self,
        *,
        modes_of: Callable[[], Mapping[str, str]],
        autonomy_preset_of: Callable[[], str] | None = None,
        denied_tools: frozenset[str] | None = None,
    ) -> None:
        self._modes_of = modes_of
        self._preset_of = autonomy_preset_of or (lambda: "ask_first")
        self._denied = denied_tools or frozenset()

    def is_allowed(self, ctx: ToolContext, spec: ToolSpec) -> bool:
        del ctx
        if spec.name in self._denied:
            return False
        return self.effective_mode(spec) != "block"

    def approval_required(self, spec: ToolSpec) -> bool:
        raw = (self._modes_of().get(spec.name) or "").strip().lower()
        mode = self.effective_mode(spec)
        if mode == "allow":
            return False
        if mode == "block":
            return True
        # Explicit Ask always asks.
        if raw == "ask":
            return True
        # Default Ask path: Balanced may auto-run reversible execute tools.
        if (
            self._preset_of() == "balanced"
            and spec.name in BALANCED_AUTO_EXECUTE
            and spec.name not in HARD_CEILING_TOOLS
            and spec.access_kind != "destructive"
        ):
            return False
        return spec.access_kind in ("execute", "destructive")

    def effective_mode(self, spec: ToolSpec) -> PermissionMode:
        raw = (self._modes_of().get(spec.name) or "").strip().lower()
        if raw not in {"allow", "ask", "block"}:
            raw = "ask" if spec.access_kind in ("execute", "destructive") else "allow"
        if raw == "allow" and (
            spec.name in HARD_CEILING_TOOLS or spec.access_kind == "destructive"
        ):
            return "ask"
        return raw


def normalize_tool_permissions(
    raw: Mapping[str, str] | None,
    *,
    known_tools: set[str] | None = None,
) -> dict[str, str]:
    """Validate and clamp owner-supplied modes. Unknown tools are dropped."""
    out: dict[str, str] = {}
    for name, mode in (raw or {}).items():
        key = str(name).strip()
        value = str(mode).strip().lower()
        if known_tools is not None and key not in known_tools:
            continue
        if value not in {"allow", "ask", "block"}:
            continue
        if value == "allow" and key in HARD_CEILING_TOOLS:
            value = "ask"
        out[key] = value
    return out


__all__ = [
    "HARD_CEILING_TOOLS",
    "OwnerPermissionPolicy",
    "PermissionMode",
    "normalize_tool_permissions",
]
