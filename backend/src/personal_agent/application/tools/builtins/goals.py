"""Goal and plan tools. Proposing never executes: plan steps run later, through the registry."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from personal_agent.application.goal_payloads import goal_payload, plan_payload
from personal_agent.application.services.goal_service import GoalService
from personal_agent.application.services.plan_service import PlanService
from personal_agent.domain.exceptions import ToolInputError
from personal_agent.domain.goals import ACCESS_ORDER, GoalError
from personal_agent.domain.models import ToolContext, ToolSpec


def goal_tools(goals: GoalService, plans: PlanService) -> list[ToolSpec]:
    def create(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        try:
            goal = goals.create(
                ctx.user_id,
                str(args["title"]),
                success_criteria=args.get("success_criteria"),
                next_step=str(args.get("next_step") or ""),
                source="agent",
            )
        except GoalError as exc:
            raise ToolInputError(str(exc)) from exc
        return json.dumps({**goal_payload(goal), "summary": f"Goal: {goal.title}"})

    def propose(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        try:
            plan = plans.propose(
                ctx.user_id,
                str(args["title"]),
                list(args["steps"]),
                goal_id=str(args["goal_id"]) if args.get("goal_id") else None,
                source="agent",
            )
        except GoalError as exc:
            raise ToolInputError(str(exc)) from exc
        count = len(plan.steps)
        summary = f"Plan: {plan.title} ({count} step{'s' if count != 1 else ''}, awaiting approval)"
        return json.dumps({**plan_payload(plan), "summary": summary})

    step_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "maxLength": 32},
            "title": {"type": "string", "minLength": 1, "maxLength": 256},
            "tool_name": {"type": "string", "maxLength": 128},
            "access_kind": {"type": "string", "enum": list(ACCESS_ORDER)},
            "depends_on": {"type": "array", "items": {"type": "string"}, "maxItems": 30},
        },
        "required": ["title"],
        "additionalProperties": False,
    }
    return [
        ToolSpec(
            name="goal_create",
            description=(
                "Create a goal the owner wants to reach, with optional success criteria and "
                "a next step. Only when the owner asks to set or track a goal."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 256},
                    "success_criteria": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1, "maxLength": 500},
                        "maxItems": 20,
                    },
                    "next_step": {"type": "string", "maxLength": 500},
                },
                "required": ["title"],
                "additionalProperties": False,
            },
            access_kind="prepare",
            handler=create,
            result_type="task",
        ),
        ToolSpec(
            name="plan_propose",
            description=(
                "Propose a step-by-step plan, optionally for a goal. This only records the "
                "plan for the owner to approve; nothing runs. Name a tool_name on a step when "
                "it needs one; sending, deleting, sharing or spending steps still need their "
                "own approval later."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 256},
                    "goal_id": {"type": "string", "maxLength": 64},
                    "steps": {"type": "array", "items": step_schema, "minItems": 1, "maxItems": 30},
                },
                "required": ["title", "steps"],
                "additionalProperties": False,
            },
            access_kind="prepare",
            handler=propose,
            result_type="plan",
        ),
    ]


__all__ = ["goal_tools"]
