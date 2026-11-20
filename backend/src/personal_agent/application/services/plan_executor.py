"""Run authorized read/prepare steps of an approved plan through the tool registry (G4)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from personal_agent.domain.exceptions import ApprovalPendingError, StorageError
from personal_agent.domain.goals import AUTHORIZED_BY_PLAN_APPROVAL, GoalError, Plan, PlanStep
from personal_agent.domain.models import ToolCall, ToolContext
from personal_agent.domain.ports import AuditLog, PlanRepository, ToolRegistry

logger = logging.getLogger(__name__)


class PlanExecutor:
    """Walks authorized steps in order; commit steps stay `needs_ok` for separate approval."""

    def __init__(
        self,
        plans: PlanRepository,
        registry: ToolRegistry,
        *,
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._plans = plans
        self._registry = registry
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    def run_authorized(self, plan_id: str, owner_user_id: str) -> Plan:
        plan = self._plans.get(plan_id)
        if plan is None or plan.owner_user_id != owner_user_id:
            raise StorageError(f"Unknown plan '{plan_id}'.")
        if plan.status != "approved":
            raise GoalError(f"Only an approved plan can run (this plan is {plan.status}).")

        now = self._clock()
        done_ids = {s.id for s in plan.steps if s.status == "done"}
        for step in plan.steps:
            if step.status != "planned":
                continue
            if step.access_kind not in AUTHORIZED_BY_PLAN_APPROVAL:
                continue
            if any(dep not in done_ids for dep in step.depends_on):
                continue
            self._run_step(plan, step, now)
            if step.status == "done":
                done_ids.add(step.id)
            elif step.status == "failed":
                break

        if all(s.status == "done" for s in plan.steps):
            plan.status = "done"
        plan.updated_at = now
        self._plans.save(plan)
        if self._audit is not None:
            self._audit.record(
                "plan.executed",
                owner_user_id,
                {
                    "plan_id": plan.id,
                    "done": [s.id for s in plan.steps if s.status == "done"],
                    "failed": [s.id for s in plan.steps if s.status == "failed"],
                    "needs_ok": [s.id for s in plan.steps if s.status == "needs_ok"],
                },
            )
        return plan

    def _run_step(self, plan: Plan, step: PlanStep, now: datetime) -> None:
        step.status = "running"
        plan.updated_at = now
        self._plans.save(plan)

        if not step.tool_name:
            step.status = "done"
            return

        ctx = ToolContext(
            user_id=plan.owner_user_id,
            session_id=f"plan:{plan.id}",
            origin="plan",
            run_id=plan.id,
        )
        call = ToolCall(id=uuid.uuid4().hex, name=step.tool_name, arguments={})
        try:
            result = self._registry.execute(call, ctx)
        except ApprovalPendingError:
            step.status = "needs_ok"
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Plan step %s failed: %s", step.id, exc)
            step.status = "failed"
            return

        step.status = "done" if result.ok else "failed"


__all__ = ["PlanExecutor"]
