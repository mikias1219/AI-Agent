"""Run an approved plan's steps in order through the tool registry (G4, BR-01..BR-09).

* read/prepare steps are authorized by the plan approval and run via `ToolRegistry.execute`.
* execute/destructive ("commit") steps are never authorized by the plan: the registry creates
  the normal durable approval, the plan pauses on that step, and it continues only after the
  owner approves (the approval service runs the tool exactly once and notifies `on_approval`).
* Steps are strictly sequential: the first step that is not `done` stops the walk.
* Every call goes through the registry, so pause gate, permission policy, argument schema,
  commit budget (BR-09) and untrusted-content labelling still apply. Nothing is called twice:
  a step is persisted as `running` before it is executed and a crashed `running` step is
  marked failed, never silently re-run.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime

from personal_agent.domain.approvals import Approval, ApprovalStatus
from personal_agent.domain.exceptions import ApprovalPendingError, StorageError
from personal_agent.domain.goals import (
    MAX_STEP_RESULT,
    GoalError,
    Plan,
    PlanStep,
)
from personal_agent.domain.models import ToolCall, ToolContext
from personal_agent.domain.ports import AuditLog, PlanRepository, ToolRegistry

logger = logging.getLogger(__name__)

CALL_PREFIX = "plan:"
UNTRUSTED_PREFIX = "[UNTRUSTED_EXTERNAL_CONTENT] "


def call_id_for(plan_id: str, step_id: str) -> str:
    return f"{CALL_PREFIX}{plan_id}:{step_id}"


def parse_call_id(call_id: str) -> tuple[str, str] | None:
    if not call_id.startswith(CALL_PREFIX):
        return None
    plan_id, _, step_id = call_id[len(CALL_PREFIX) :].partition(":")
    return (plan_id, step_id) if plan_id and step_id else None


ApprovalLookup = Callable[[str], Approval | None]


class PlanExecutor:
    def __init__(
        self,
        plans: PlanRepository,
        registry: ToolRegistry,
        *,
        approvals: ApprovalLookup | None = None,
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._plans = plans
        self._registry = registry
        self._approvals = approvals
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.RLock()

    # -- entry points -------------------------------------------------------------

    def run_authorized(self, plan_id: str, owner_user_id: str) -> Plan:
        """Walk the plan until it finishes, fails or pauses on a commit step."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None or plan.owner_user_id != owner_user_id:
                raise StorageError(f"Unknown plan '{plan_id}'.")
            if plan.status != "approved":
                raise GoalError(f"Only an approved plan can run (this plan is {plan.status}).")
            self._walk(plan)
            return plan

    def on_approval(self, approval: Approval) -> None:
        """Approval service hook: a plan's commit step was decided; continue the plan."""
        parsed = parse_call_id(approval.call_id)
        if parsed is None:
            return
        try:
            self.run_authorized(parsed[0], approval.user_id)
        except (StorageError, GoalError):
            logger.info("Plan %s could not continue after approval.", parsed[0])
        except Exception:  # noqa: BLE001 — never break the approval decision
            logger.exception("Plan continuation failed for approval %s.", approval.id)

    # -- internals -------------------------------------------------------------------

    def _walk(self, plan: Plan) -> None:
        now = self._clock()
        untrusted_tools = {s.name for s in self._registry.specs() if s.untrusted_output}
        ctx = ToolContext(
            user_id=plan.owner_user_id,
            session_id=f"plan:{plan.id}",
            origin="plan",
            run_id=plan.id,
            # BR-04: anything an earlier step read from outside taints later approvals.
            untrusted_content=any(
                s.status == "done" and s.tool_name in untrusted_tools for s in plan.steps
            ),
        )
        for step in plan.steps:
            if step.status == "done":
                continue
            if not self._advance(plan, step, ctx, untrusted_tools):
                break
        if all(s.status == "done" for s in plan.steps):
            plan.status = "done"
        plan.updated_at = now
        self._plans.save(plan)
        if self._audit is not None:
            self._audit.record(
                "plan.executed",
                plan.owner_user_id,
                {
                    "plan_id": plan.id,
                    "done": [s.id for s in plan.steps if s.status == "done"],
                    "failed": [s.id for s in plan.steps if s.status == "failed"],
                    "needs_ok": [s.id for s in plan.steps if s.status == "needs_ok"],
                },
            )

    def _advance(
        self, plan: Plan, step: PlanStep, ctx: ToolContext, untrusted_tools: set[str]
    ) -> bool:
        """Try to finish one step. True means it is done and the walk may continue."""
        done_ids = {s.id for s in plan.steps if s.status == "done"}
        if any(dep not in done_ids for dep in step.depends_on):
            return False
        if step.status == "failed":
            return False
        if step.status == "running":
            # Interrupted mid-flight: we cannot know whether it took effect. Never re-run.
            self._fail(plan, step, "Interrupted before finishing; not re-run automatically.")
            return False
        if step.status == "needs_ok" and step.approval_id:
            return self._check_approval(plan, step, untrusted_tools)
        if step.status not in ("planned", "needs_ok"):
            return False
        if not step.tool_name:
            step.status = "done"
            self._plans.save(plan)
            return True
        return self._execute(plan, step, ctx, untrusted_tools)

    def _execute(
        self, plan: Plan, step: PlanStep, ctx: ToolContext, untrusted_tools: set[str]
    ) -> bool:
        step.status = "running"
        self._plans.save(plan)
        call = ToolCall(
            id=call_id_for(plan.id, step.id), name=step.tool_name or "", arguments=step.arguments
        )
        try:
            result = self._registry.execute(call, ctx)
        except ApprovalPendingError as pending:
            step.status = "needs_ok"
            step.approval_id = pending.approval_id
            step.result = "Waiting for your approval."
            self._plans.save(plan)
            return False
        except Exception as exc:  # noqa: BLE001 — policy, schema, pause, unknown tool
            self._fail(plan, step, str(exc))
            return False
        if not result.ok:
            self._fail(plan, step, result.error or "Tool failed.")
            return False
        self._finish(plan, step, result.output, untrusted_tools)
        if step.tool_name in untrusted_tools:
            ctx.untrusted_content = True
        return True

    def _check_approval(self, plan: Plan, step: PlanStep, untrusted_tools: set[str]) -> bool:
        approval = self._approvals(step.approval_id or "") if self._approvals else None
        if approval is None:
            return False  # cannot tell; stay paused
        if approval.status is ApprovalStatus.EXECUTED:
            self._finish(plan, step, approval.result, untrusted_tools)
            return True
        if approval.status is ApprovalStatus.SUPERSEDED:
            return False  # edited: a newer approval carries on; owner resumes later
        if approval.status in (
            ApprovalStatus.DENIED,
            ApprovalStatus.FAILED,
            ApprovalStatus.EXPIRED,
        ):
            self._fail(plan, step, f"Approval {approval.status.value}.")
        return False  # pending / approved-but-not-yet-run: stay paused

    def _finish(self, plan: Plan, step: PlanStep, output: str, untrusted_tools: set[str]) -> None:
        text = output or ""
        if step.tool_name in untrusted_tools:
            text = UNTRUSTED_PREFIX + text
        step.result = text[:MAX_STEP_RESULT]
        step.status = "done"
        self._plans.save(plan)

    def _fail(self, plan: Plan, step: PlanStep, reason: str) -> None:
        logger.warning("Plan %s step %s failed: %s", plan.id, step.id, reason)
        step.status = "failed"
        step.result = reason[:MAX_STEP_RESULT]
        self._plans.save(plan)


__all__ = ["PlanExecutor", "call_id_for", "parse_call_id"]
