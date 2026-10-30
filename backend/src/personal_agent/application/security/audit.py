"""Security-flavored audit events, built on the `domain.ports.AuditLog` sink.

The registry and gateways already record their decisions; these helpers give
application code a uniform vocabulary for the events ops tooling will filter on.
Values that look like secrets are dropped by the sink's redaction filter.
"""

from __future__ import annotations

from personal_agent.domain.models import ToolContext
from personal_agent.domain.ports import AuditLog


def log_permission_denied(audit: AuditLog, ctx: ToolContext, tool_name: str, reason: str) -> None:
    """Record that the policy refused a tool execution."""
    audit.record(
        "security.permission_denied",
        ctx.user_id,
        {"tool": tool_name, "reason": reason, "origin": ctx.origin, "session": ctx.session_id},
    )


def log_credential_use(audit: AuditLog, actor: str, service: str, scope: str) -> None:
    """Record that credentials for a service were exercised (never the secret itself)."""
    audit.record(
        "security.credential_used",
        actor,
        {"service": service, "scope": scope},
    )
