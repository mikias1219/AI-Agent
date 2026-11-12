"""Plans: propose, list, approve, cancel (spec §9.2).

Approving a plan authorizes READ/PREPARE steps only. `execute`/`destructive` steps become
`needs_ok` and still pass the ToolRegistry approval gate whenever they actually run. This
service never executes a tool.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.goals import (
    GoalError,
    Plan,
    PlanStep,
    approve_plan,
    cancel_plan,
    check_access_kind,
    clean_title,
    stricter_access,
    validate_steps,
)
from personal_agent.domain.ports import AuditLog, GoalRepository, PlanRepository

AccessKindOf = Callable[[str], str | None]
_Steps = list[PlanStep]


def build_steps(
    raw_steps: Sequence[Mapping[str, Any]], access_kind_of: AccessKindOf | None
) -> _Steps:
    """Normalize proposed steps; a step's access kind is never lower than its tool's."""
    steps: _Steps = []
    for index, raw in enumerate(raw_steps, start=1):
        tool_name = str(raw["tool_name"]).strip() if raw.get("tool_name") else None
        actual = access_kind_of(tool_name) if tool_name and access_kind_of else None
        if tool_name and access_kind_of is not None and actual is None:
            raise GoalError(f"Step {index} names unknown tool '{tool_name}'.")
        declared = check_access_kind(str(raw.get("access_kind") or "prepare"))
        steps.append(
            PlanStep(
                id=str(raw.get("id") or f"s{index}"),
                title=clean_title(str(raw.get("title", "")), what=f"Step {index} title"),
                tool_name=tool_name,
                access_kind=stricter_access(declared, actual),
                status="planned",
                depends_on=[str(d) for d in raw.get("depends_on") or []],
            )
        )
    validate_steps(steps)
    return steps


class PlanService:
    def __init__(
        self,
        repository: PlanRepository,
        goals: GoalRepository,
        *,
        access_kind_of: AccessKindOf | None = None,
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._goals = goals
        # Resolves a tool name to its registered access_kind (None = no such tool).
        self._access_kind_of = access_kind_of
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    def propose(
        self,
        owner_user_id: str,
        title: str,
        steps: Sequence[Mapping[str, Any]],
        *,
        goal_id: str | None = None,
        source: str = "owner",
    ) -> Plan:
        if goal_id is not None:
            goal = self._goals.get(goal_id)
            if goal is None or goal.owner_user_id != owner_user_id:
                raise StorageError(f"Unknown goal '{goal_id}'.")
        now = self._clock()
        plan = Plan(
            id=uuid.uuid4().hex,
            goal_id=goal_id,
            owner_user_id=owner_user_id,
            title=clean_title(title, what="Plan title"),
            steps=self._build_steps(steps),
            status="proposed",
            created_at=now,
            updated_at=now,
        )
        self._repository.add(plan)
        self._record("plan.proposed", plan, source=source, steps=len(plan.steps))
        return plan

    def get(self, plan_id: str, owner_user_id: str) -> Plan:
        plan = self._repository.get(plan_id)
        if plan is None or plan.owner_user_id != owner_user_id:
            raise StorageError(f"Unknown plan '{plan_id}'.")
        return plan

    def list(self, owner_user_id: str, goal_id: str | None = None) -> Sequence[Plan]:
        return self._repository.list(owner_user_id, goal_id)

    def approve(self, plan_id: str, owner_user_id: str) -> Plan:
        plan = self.get(plan_id, owner_user_id)
        # Re-resolve every step against the live registry: a tool may have been reclassified
        # since the plan was proposed, and approval must never lower a ceiling.
        for step in plan.steps:
            step.access_kind = stricter_access(step.access_kind, self._actual(step.tool_name))
        approve_plan(plan, now=self._clock())
        self._repository.save(plan)
        self._record(
            "plan.approved",
            plan,
            authorized=[s.id for s in plan.steps if s.status == "planned"],
            needs_ok=[s.id for s in plan.steps if s.status == "needs_ok"],
        )
        return plan

    def cancel(self, plan_id: str, owner_user_id: str) -> Plan:
        plan = self.get(plan_id, owner_user_id)
        cancel_plan(plan, now=self._clock())
        self._repository.save(plan)
        self._record("plan.cancelled", plan)
        return plan

    # -- internals ------------------------------------------------------------

    def _actual(self, tool_name: str | None) -> str | None:
        if tool_name is None or self._access_kind_of is None:
            return None
        return self._access_kind_of(tool_name)

    def _build_steps(self, raw_steps: Sequence[Mapping[str, Any]]) -> _Steps:
        return build_steps(raw_steps, self._access_kind_of)

    def _record(self, event: str, plan: Plan, **details: object) -> None:
        if self._audit is not None:
            self._audit.record(
                event,
                plan.owner_user_id,
                {"plan_id": plan.id, "goal_id": plan.goal_id, **details},
            )
