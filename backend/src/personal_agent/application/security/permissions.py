"""Permission policy — the single place that decides what the agent may do.

Today, policy is deliberately simple (single-user CLI, everything local):

- `denied_tools`  → hard-deny regardless of anything the model says.
- `execute`-kind tools always require human approval.
- `approval_tools` → extra tools that require approval even though they are not
  `execute`-kind (e.g. an expensive prepare action).

When multi-user-auth arrives later, extend `is_allowed` with roles/username checks
here — call sites do not change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from personal_agent.domain.models import ToolContext, ToolSpec


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    """Immutable policy consulted by the tool registry on every execution."""

    denied_tools: frozenset[str] = field(default_factory=frozenset)
    approval_tools: frozenset[str] = field(default_factory=frozenset)

    def is_allowed(self, ctx: ToolContext, spec: ToolSpec) -> bool:
        """Is this tool usable at all in this context? (No side effects implied.)"""
        del ctx  # context-aware rules (per-user/per-origin) attach here later
        return spec.name not in self.denied_tools

    def approval_required(self, spec: ToolSpec) -> bool:
        """Does this action need a human decision before it may run?"""
        return spec.access_kind == "execute" or spec.name in self.approval_tools


DEFAULT_POLICY = PermissionPolicy(
    denied_tools=frozenset(),
    approval_tools=frozenset(),
)
