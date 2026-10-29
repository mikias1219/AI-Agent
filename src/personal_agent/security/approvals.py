"""Human-in-the-loop approvals.

When a risky action is requested, `ApprovalGatewayImpl` persists a pending row, asks
the *notifier* (a callback the interface layer provides — the CLI prompts; an API
would notify a dashboard), and turns the answer into an audit + decision record.
If no notifier is wired (tests, API before its dashboard exists), the request is
`deferred`: nothing runs, the row stays pending for a human to resolve later.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from personal_agent.core.errors import StorageError
from personal_agent.core.ports import AuditLog
from personal_agent.core.types import ApprovalDecision, ToolCall, ToolContext

logger = logging.getLogger(__name__)


@runtime_checkable
class ApprovalRepository(Protocol):
    """Persistence contract owned here so storage stays an outside detail."""

    def create_pending(
        self, approval_id: str, call: ToolCall, ctx: ToolContext
    ) -> None: ...

    def decision(self, approval_id: str) -> str | None: ...

    def update_status(self, approval_id: str, status: str) -> None: ...


Notifier = Callable[[str, Mapping[str, Any]], "ApprovalDecision"]


class ApprovalGatewayImpl:
    """Implements `core.ports.ApprovalGateway` against an `ApprovalRepository`."""

    def __init__(
        self,
        repo: ApprovalRepository,
        audit: AuditLog,
        notifier: Notifier | None = None,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._notifier = notifier

    def request(self, call: ToolCall, ctx: ToolContext) -> ApprovalDecision:
        """Ask a human; only 'approved' lets the registry run the handler."""
        import uuid

        approval_id = uuid.uuid4().hex
        try:
            self._repo.create_pending(approval_id, call, ctx)
        except Exception as exc:
            raise StorageError(f"Could not record approval request: {exc}") from exc

        prompt = (
            f"Request approval to use tool '{call.name}' with args={call.arguments!r} "
            f"[approval id: {approval_id[:8]}]?"
        )
        audit_details = {
            "tool": call.name,
            "approval_id": approval_id,
            "origin": ctx.origin,
        }

        decision: ApprovalDecision = "deferred"
        if self._notifier is not None:
            try:
                decision = self._notifier(prompt, dict(audit_details))
            except Exception as exc:
                logger.warning("Approval notifier failed: %s", exc)
                decision = "deferred"
        else:
            logger.info(
                "Approval for tool '%s' is pending (id=%s). No notifier configured.",
                call.name,
                approval_id,
            )

        if decision == "deferred":
            self._audit.record("approval.deferred", ctx.user_id, audit_details)
            return "deferred"

        self._repo.update_status(approval_id, decision)  # 'approved' | 'denied'
        self._audit.record("approval.decided", ctx.user_id, {**audit_details, "decision": decision})
        return decision

    def decide(self, approval_id: str, approve: bool) -> None:
        """Apply a human decision made later (API, Telegram message, dashboard)."""
        status = "approved" if approve else "denied"
        self._repo.update_status(approval_id, status)
        self._audit.record(
            "approval.decided", "human", {"approval_id": approval_id, "decision": status}
        )
