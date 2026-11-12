"""JSON-friendly shapes for goals and plans, shared by the HTTP API and the tools."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from personal_agent.domain.goals import Goal, Plan, PlanStep


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def step_payload(step: PlanStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "title": step.title,
        "tool_name": step.tool_name,
        "access_kind": step.access_kind,
        "status": step.status,
        "depends_on": list(step.depends_on),
    }


def plan_payload(plan: Plan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "goal_id": plan.goal_id,
        "title": plan.title,
        "status": plan.status,
        "steps": [step_payload(s) for s in plan.steps],
        "created_at": _iso(plan.created_at),
        "updated_at": _iso(plan.updated_at),
        "approved_at": _iso(plan.approved_at),
    }


def goal_payload(goal: Goal, plans: list[Plan] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": goal.id,
        "title": goal.title,
        "success_criteria": list(goal.success_criteria),
        "progress": goal.progress,
        "status": goal.status,
        "next_step": goal.next_step,
        "created_at": _iso(goal.created_at),
        "updated_at": _iso(goal.updated_at),
    }
    if plans is not None:
        payload["plans"] = [plan_payload(p) for p in plans]
    return payload
