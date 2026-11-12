"""Deciding approvals: execute once, resume the run, report the outcome (APR-02..06).

The decision API calls `decide`. The first approval of a pending request flips it to
`approved` with a compare-and-set, runs the tool through `ToolRegistry.execute` (whose
gate claims the approval exactly once, BR-03) and then asks the run service to resume the
paused run so AURA reports the result in the originating channel. Repeating the same
decision is harmless and returns the recorded outcome without executing again.

Editing the arguments never changes an approval in place: it supersedes the old one and
creates a new pending approval with a new hash, which the owner must approve again (APR-06).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import jsonschema

from personal_agent.application.onboarding_marker import OnboardingMarker
from personal_agent.domain.approvals import (
    DECIDING_CHANNELS,
    DEFAULT_APPROVAL_TTL,
    Approval,
    ApprovalStatus,
    arguments_hash,
    declined_message,
)
from personal_agent.domain.exceptions import (
    AgentError,
    ApprovalConflictError,
    ApprovalForbiddenError,
    StorageError,
    ToolInputError,
)
from personal_agent.domain.models import ToolCall, ToolContext
from personal_agent.domain.ports import ApprovalStore, AuditLog, ToolRegistry

logger = logging.getLogger(__name__)


class RunResumer(Protocol):
    """What the approval service needs from the run owner (implemented by RunService)."""

    def resume_after_execution(
        self, approval: Approval, *, output: str, ok: bool, wait: bool = False
    ) -> None: ...

    def conclude_declined(self, approval: Approval, *, message: str) -> None: ...


@dataclass(slots=True)
class ApprovalOutcome:
    """Result of a decision call."""

    approval: Approval
    decision: str  # "approved" | "denied"
    executed: bool  # True only for the call that actually ran the tool
    ok: bool | None = None
    output: str = ""


class ApprovalService:
    def __init__(
        self,
        *,
        store: ApprovalStore,
        registry: ToolRegistry,
        audit: AuditLog,
        resumer: RunResumer | None = None,
        ttl: timedelta = DEFAULT_APPROVAL_TTL,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        onboarding: OnboardingMarker | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._audit = audit
        self._resumer = resumer
        self._ttl = ttl
        self._clock = clock
        self._onboarding = onboarding

    def bind_resumer(self, resumer: RunResumer) -> None:
        self._resumer = resumer

    # -- reads ---------------------------------------------------------------

    def get(self, approval_id: str) -> Approval:
        approval = self._store.get(approval_id)
        if approval is None:
            raise StorageError("Unknown approval.")
        return approval

    def list_approvals(
        self, status: ApprovalStatus | None = None, limit: int = 50
    ) -> list[Approval]:
        self.expire_due()
        return self._store.find(status=status, limit=limit)

    def for_run(self, run_id: str) -> list[Approval]:
        return self._store.find(run_id=run_id, limit=20)

    # -- expiry (APR-05) -------------------------------------------------------

    def expire_due(self) -> list[Approval]:
        """Expire overdue pending approvals and tell the owner on the paused run."""
        now = self._clock()
        expired: list[Approval] = []
        for approval in self._store.list_expired(now):
            if self._expire(approval, now):
                expired.append(approval)
        return expired

    def _expire(self, approval: Approval, now: datetime) -> bool:
        if not self._store.transition(
            approval.id,
            [ApprovalStatus.PENDING],
            ApprovalStatus.EXPIRED,
            now=now,
            decided_by="system",
            channel="expiry",
        ):
            return False
        self._audit.record(
            "approval.expired",
            "system",
            {"approval_id": approval.id, "tool": approval.tool_name},
        )
        current = self.get(approval.id)
        if self._resumer is not None and approval.run_id:
            self._resumer.conclude_declined(
                current, message=declined_message(ApprovalStatus.EXPIRED, approval.summary)
            )
        return True

    # -- deciding ----------------------------------------------------------------

    def decide(
        self,
        approval_id: str,
        approve: bool,
        *,
        actor: str,
        channel: str,
        wait: bool = False,
    ) -> ApprovalOutcome:
        """Apply the owner's decision. Safe to call twice: the tool runs at most once."""
        self._check_channel(channel)
        approval = self.get(approval_id)
        now = self._clock()

        if approval.status is ApprovalStatus.PENDING and approval.is_expired(now):
            self._expire(approval, now)
            approval = self.get(approval_id)

        if approval.status is ApprovalStatus.EXPIRED:
            raise ApprovalConflictError("This approval expired. Ask AURA to try again.")

        if not approve:
            return self._deny(approval, actor, channel, now)
        return self._approve(approval, actor, channel, now, wait)

    def _check_channel(self, channel: str) -> None:
        if channel not in DECIDING_CHANNELS:
            raise ApprovalForbiddenError(
                "Approvals can only be decided from the dashboard or the owner's private chat."
            )

    def _deny(self, approval: Approval, actor: str, channel: str, now: datetime) -> ApprovalOutcome:
        if approval.status is ApprovalStatus.DENIED:
            return ApprovalOutcome(approval, "denied", executed=False)
        if approval.status is not ApprovalStatus.PENDING:
            raise ApprovalConflictError(f"This approval is already {approval.status.value}.")
        moved = self._store.transition(
            approval.id,
            [ApprovalStatus.PENDING],
            ApprovalStatus.DENIED,
            now=now,
            decided_by=actor,
            channel=channel,
        )
        current = self.get(approval.id)
        if not moved:
            if current.status is ApprovalStatus.DENIED:
                return ApprovalOutcome(current, "denied", executed=False)
            raise ApprovalConflictError(f"This approval is already {current.status.value}.")
        self._audit.record(
            "approval.decided",
            actor,
            {
                "approval_id": approval.id,
                "decision": "denied",
                "tool": approval.tool_name,
                "channel": channel,
            },
        )
        if self._resumer is not None and approval.run_id:
            self._resumer.conclude_declined(
                current, message=declined_message(ApprovalStatus.DENIED, approval.summary)
            )
        return ApprovalOutcome(current, "denied", executed=False)

    def _approve(
        self, approval: Approval, actor: str, channel: str, now: datetime, wait: bool
    ) -> ApprovalOutcome:
        if approval.status in (ApprovalStatus.EXECUTED, ApprovalStatus.FAILED):
            return self._already_done(approval)
        if approval.status in (ApprovalStatus.DENIED, ApprovalStatus.SUPERSEDED):
            raise ApprovalConflictError(f"This approval is already {approval.status.value}.")

        if approval.status is ApprovalStatus.PENDING:
            moved = self._store.transition(
                approval.id,
                [ApprovalStatus.PENDING],
                ApprovalStatus.APPROVED,
                now=now,
                decided_by=actor,
                channel=channel,
            )
            if moved:
                self._audit.record(
                    "approval.decided",
                    actor,
                    {
                        "approval_id": approval.id,
                        "decision": "approved",
                        "tool": approval.tool_name,
                        "arguments_hash": approval.arguments_hash,
                        "channel": channel,
                    },
                )
                if self._onboarding is not None:
                    try:
                        self._onboarding.mark(approval.user_id, "approved_action")
                    except Exception:  # noqa: BLE001
                        logger.exception("Could not mark approved_action checklist item")
        approval = self.get(approval.id)
        if approval.status is not ApprovalStatus.APPROVED:
            # Lost the race to a concurrent decision that already progressed it.
            if approval.status in (ApprovalStatus.EXECUTED, ApprovalStatus.FAILED):
                return self._already_done(approval)
            raise ApprovalConflictError(f"This approval is already {approval.status.value}.")
        return self._execute(approval, wait)

    @staticmethod
    def _already_done(approval: Approval) -> ApprovalOutcome:
        return ApprovalOutcome(
            approval,
            "approved",
            executed=False,
            ok=approval.status is ApprovalStatus.EXECUTED,
            output=approval.result,
        )

    def _execute(self, approval: Approval, wait: bool) -> ApprovalOutcome:
        """Run the approved tool through the registry gate, which claims it exactly once."""
        call = ToolCall(id=approval.call_id, name=approval.tool_name, arguments=approval.arguments)
        ctx = ToolContext(
            user_id=approval.user_id,
            session_id=approval.session_id,
            origin=approval.origin,
            run_id=approval.run_id,
            approval_id=approval.id,
            untrusted_content=approval.untrusted_content,
        )
        try:
            result = self._registry.execute(call, ctx)
            ok, output = result.ok, (result.output if result.ok else result.error or "tool failed")
        except AgentError as exc:
            current = self.get(approval.id)
            if current.status in (ApprovalStatus.EXECUTED, ApprovalStatus.FAILED):
                return self._already_done(current)  # another caller claimed it first
            if current.status is not ApprovalStatus.APPROVED:
                return ApprovalOutcome(current, "approved", False, ok=False, output=str(exc))
            # The gate refused before claiming (bad arguments, policy): record the failure.
            ok, output = False, str(exc)
            self._store.transition(
                approval.id,
                [ApprovalStatus.APPROVED],
                ApprovalStatus.FAILED,
                now=self._clock(),
                result=output[:4000],
            )

        final = self.get(approval.id)
        if self._resumer is not None and approval.run_id:
            self._resumer.resume_after_execution(final, output=output, ok=ok, wait=wait)
        return ApprovalOutcome(final, "approved", executed=True, ok=ok, output=output)

    # -- edit then approve (APR-06) -------------------------------------------------

    def edit(
        self,
        approval_id: str,
        arguments: Mapping[str, Any],
        *,
        actor: str,
        channel: str,
    ) -> Approval:
        """Replace a pending approval with an edited one that needs its own approval."""
        self._check_channel(channel)
        approval = self.get(approval_id)
        now = self._clock()
        if approval.status is not ApprovalStatus.PENDING or approval.is_expired(now):
            raise ApprovalConflictError("Only a pending approval can be edited.")
        edited = json.loads(json.dumps(dict(arguments)))
        self._validate_arguments(approval.tool_name, edited)
        new_hash = arguments_hash(edited)
        if new_hash == approval.arguments_hash:
            raise ApprovalConflictError("The arguments are unchanged; approve this request.")

        if not self._store.transition(
            approval.id,
            [ApprovalStatus.PENDING],
            ApprovalStatus.SUPERSEDED,
            now=now,
            decided_by=actor,
            channel=channel,
        ):
            raise ApprovalConflictError("This approval was already decided.")
        replacement = Approval(
            id=uuid.uuid4().hex,
            tool_name=approval.tool_name,
            arguments=edited,
            arguments_hash=new_hash,
            user_id=approval.user_id,
            session_id=approval.session_id,
            origin=approval.origin,
            run_id=approval.run_id,
            call_id=approval.call_id,
            risk=approval.risk,
            summary=approval.summary,
            untrusted_content=approval.untrusted_content,
            created_at=now,
            expires_at=now + self._ttl,
            edited_from=approval.id,
        )
        self._store.create(replacement)
        self._audit.record(
            "approval.edited",
            actor,
            {
                "tool": approval.tool_name,
                "old_approval_id": approval.id,
                "new_approval_id": replacement.id,
                "old_hash": approval.arguments_hash,
                "new_hash": new_hash,
                "channel": channel,
            },
        )
        return replacement

    def _validate_arguments(self, tool_name: str, arguments: dict[str, Any]) -> None:
        spec = next((s for s in self._registry.specs() if s.name == tool_name), None)
        if spec is None:
            raise ToolInputError(f"No tool named '{tool_name}' is registered.")
        try:
            jsonschema.validate(instance=arguments, schema=dict(spec.parameters_schema))
        except jsonschema.ValidationError as exc:
            raise ToolInputError(f"Bad arguments for '{tool_name}': {exc.message}") from exc
