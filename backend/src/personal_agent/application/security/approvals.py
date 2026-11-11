"""Human-in-the-loop approvals (APR-01..06).

`ApprovalGatewayImpl` persists every approval request (arguments, hash, risk, expiry) and
then does one of three things:

- an *interactive* notifier is wired (CLI): ask inline and return the answer;
- *durable* mode (dashboard, Telegram): leave the row pending and raise
  `ApprovalPendingError` so the run pauses and releases its thread — the decision arrives
  later through `ApprovalService`, even after a restart;
- neither: the request is `deferred`; nothing runs and the row stays pending.

An approved action runs once: `claim` flips `approved -> executed` in a single atomic
update, after checking the tool and the arguments hash (BR-03).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from personal_agent.application.run_events import emit_event
from personal_agent.domain.approvals import (
    DEFAULT_APPROVAL_TTL,
    Approval,
    ApprovalStatus,
    arguments_hash,
    risk_level,
    summarize_call,
)
from personal_agent.domain.exceptions import (
    ApprovalPendingError,
    PermissionDeniedError,
    StorageError,
)
from personal_agent.domain.models import ApprovalDecision, ToolCall, ToolContext
from personal_agent.domain.ports import ApprovalStore, AuditLog

logger = logging.getLogger(__name__)

ApprovalRepository = ApprovalStore  # the port lives in the domain; kept for old imports

Notifier = Callable[[str, Mapping[str, Any]], "ApprovalDecision"]


def approval_event_data(approval: Approval, *, durable: bool) -> dict[str, Any]:
    """Payload of the `approval.required` event: everything the card needs."""
    return {
        "approval_id": approval.id,
        "tool": approval.tool_name,
        "arguments": dict(approval.arguments),
        "summary": approval.summary,
        "risk": approval.risk,
        "untrusted_content": approval.untrusted_content,
        "arguments_hash": approval.arguments_hash,
        "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        "durable": durable,
    }


class ApprovalGatewayImpl:
    """Implements `domain.ports.ApprovalGateway` against an `ApprovalStore`."""

    def __init__(
        self,
        repo: ApprovalStore,
        audit: AuditLog,
        notifier: Notifier | None = None,
        *,
        durable: bool = False,
        ttl: timedelta = DEFAULT_APPROVAL_TTL,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._notifier = notifier
        self._durable = durable
        self._ttl = ttl
        self._clock = clock

    # -- requesting ------------------------------------------------------------

    def request(
        self,
        call: ToolCall,
        ctx: ToolContext,
        *,
        access_kind: str = "execute",
        description: str = "",
    ) -> ApprovalDecision:
        """Record the request, then ask inline, pause (durable) or defer."""
        now = self._clock()
        approval = Approval(
            id=uuid.uuid4().hex,
            tool_name=call.name,
            arguments=dict(call.arguments),
            arguments_hash=arguments_hash(call.arguments),
            user_id=ctx.user_id,
            session_id=ctx.session_id,
            origin=ctx.origin,
            run_id=ctx.run_id,
            call_id=call.id,
            risk=risk_level(access_kind, call.name),
            summary=summarize_call(call.name, description),
            untrusted_content=ctx.untrusted_content,
            created_at=now,
            expires_at=now + self._ttl,
        )
        try:
            self._repo.create(approval)
        except Exception as exc:
            raise StorageError(f"Could not record approval request: {exc}") from exc

        audit_details = {
            "tool": call.name,
            "approval_id": approval.id,
            "origin": ctx.origin,
            "arguments_hash": approval.arguments_hash,
        }
        durable_pause = self._notifier is None and self._durable
        emit_event(ctx, "approval.required", **approval_event_data(approval, durable=durable_pause))

        decision: ApprovalDecision = "deferred"
        if self._notifier is not None:
            prompt = (
                f"Request approval to use tool '{call.name}' with args={call.arguments!r} "
                f"[approval id: {approval.id[:8]}]?"
            )
            try:
                decision = self._notifier(prompt, dict(audit_details))
            except Exception as exc:
                logger.warning("Approval notifier failed: %s", exc)
                decision = "deferred"
        elif durable_pause:
            self._audit.record("approval.requested", ctx.user_id, audit_details)
            raise ApprovalPendingError(approval.id, call.name)
        else:
            logger.info(
                "Approval for tool '%s' is pending (id=%s). No notifier configured.",
                call.name,
                approval.id,
            )

        if decision == "deferred":
            self._audit.record("approval.deferred", ctx.user_id, audit_details)
            emit_event(ctx, "approval.resolved", approval_id=approval.id, decision="deferred")
            return "deferred"

        status = ApprovalStatus.APPROVED if decision == "approved" else ApprovalStatus.DENIED
        if not self._repo.transition(
            approval.id,
            [ApprovalStatus.PENDING],
            status,
            now=self._clock(),
            decided_by=ctx.user_id,
            channel=ctx.origin,
        ):
            current = self._repo.get(approval.id)
            decision = "approved" if current and current.status.value == "approved" else "denied"
        self._audit.record("approval.decided", ctx.user_id, {**audit_details, "decision": decision})
        emit_event(ctx, "approval.resolved", approval_id=approval.id, decision=decision)
        return decision

    # -- executing an approved action ---------------------------------------------

    def claim(self, approval_id: str, call: ToolCall, ctx: ToolContext) -> None:
        """Consume the approval for exactly this call; at most one caller ever succeeds."""
        approval = self._repo.get(approval_id)
        now = self._clock()
        problem = self._claim_problem(approval, call, now)
        if problem:
            self._audit.record(
                "approval.claim_rejected",
                ctx.user_id,
                {"approval_id": approval_id, "tool": call.name, "reason": problem},
            )
            raise PermissionDeniedError(f"Tool '{call.name}' cannot run: {problem}")
        if not self._repo.transition(
            approval_id, [ApprovalStatus.APPROVED], ApprovalStatus.EXECUTED, now=now
        ):
            self._audit.record(
                "approval.claim_rejected",
                ctx.user_id,
                {"approval_id": approval_id, "tool": call.name, "reason": "already used"},
            )
            raise PermissionDeniedError(
                f"Tool '{call.name}' cannot run: this approval was already used."
            )

    @staticmethod
    def _claim_problem(approval: Approval | None, call: ToolCall, now: datetime) -> str:
        if approval is None:
            return "unknown approval."
        if approval.status is not ApprovalStatus.APPROVED:
            return f"approval is {approval.status.value}, not approved."
        if approval.is_expired(now):
            return "approval expired."
        if approval.tool_name != call.name:
            return "approval was for a different tool."
        digest = arguments_hash(call.arguments)
        if digest != approval.arguments_hash or arguments_hash(approval.arguments) != digest:
            return "arguments differ from what was approved."
        return ""

    def finish(self, approval_id: str, *, ok: bool, result: str) -> None:
        """Record the execution outcome on the approval row."""
        self._repo.transition(
            approval_id,
            [ApprovalStatus.EXECUTED],
            ApprovalStatus.EXECUTED if ok else ApprovalStatus.FAILED,
            now=self._clock(),
            result=result[:4000],
        )
