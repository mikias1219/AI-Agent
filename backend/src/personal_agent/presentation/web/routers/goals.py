"""Goals and plans (Phase 6 split)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer
from personal_agent.application.goal_payloads import goal_payload, plan_payload
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.goals import GoalError
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER


class GoalCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    success_criteria: list[str] = Field(default_factory=list, max_length=20)
    next_step: str = Field(default="", max_length=500)
    kind: str = Field(default="goal", max_length=16)
    target_hours: float | None = Field(default=None, gt=0, le=10_000)
    milestones: list[dict[str, Any] | str] = Field(default_factory=list, max_length=50)


class GoalPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    success_criteria: list[str] | None = Field(default=None, max_length=20)
    progress: float | None = None
    status: str | None = Field(default=None, max_length=16)
    next_step: str | None = Field(default=None, max_length=500)
    kind: str | None = Field(default=None, max_length=16)
    target_hours: float | None = Field(default=None, gt=0, le=10_000)
    milestones: list[dict[str, Any] | str] | None = Field(default=None, max_length=50)


class PlanStepRequest(BaseModel):
    id: str | None = Field(default=None, max_length=32)
    title: str = Field(min_length=1, max_length=256)
    tool_name: str | None = Field(default=None, max_length=128)
    access_kind: str | None = Field(default=None, max_length=16)
    depends_on: list[str] = Field(default_factory=list, max_length=30)
    arguments: dict[str, Any] = Field(default_factory=dict)


class PlanCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    goal_id: str | None = Field(default=None, max_length=64)
    steps: list[PlanStepRequest] = Field(min_length=1, max_length=30)


def build_goals_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["goals"])

    def goal_response(goal_id: str) -> dict[str, Any]:
        goal = container.goals.get(goal_id, DASHBOARD_OWNER)
        return with_hours(
            goal_payload(goal, container.plans.list(DASHBOARD_OWNER, goal_id=goal.id))
        )

    def with_hours(payload: dict[str, Any]) -> dict[str, Any]:
        """Study time comes from time entries linked to the goal."""
        minutes = container.time.minutes_for_goal(DASHBOARD_OWNER, payload["id"])
        payload["studied_hours"] = round(minutes / 60, 1)
        return payload

    def goal_error(exc: Exception) -> HTTPException:
        if isinstance(exc, StorageError):
            return HTTPException(status_code=404, detail=str(exc))
        return HTTPException(status_code=422, detail=str(exc))

    @router.get("/api/goals")
    def list_goals(
        status: Annotated[str | None, Query(max_length=16)] = None,
    ) -> list[dict[str, Any]]:
        try:
            goals = container.goals.list(DASHBOARD_OWNER, status)
        except GoalError as exc:
            raise goal_error(exc) from exc
        return [with_hours(goal_payload(g)) for g in goals]

    @router.post("/api/goals", status_code=201)
    def create_goal(request: GoalCreateRequest) -> dict[str, Any]:
        try:
            goal = container.goals.create(
                DASHBOARD_OWNER,
                request.title,
                success_criteria=request.success_criteria,
                next_step=request.next_step,
                kind=request.kind,
                target_hours=request.target_hours,
                milestones=request.milestones,
            )
        except GoalError as exc:
            raise goal_error(exc) from exc
        return with_hours(goal_payload(goal, []))

    @router.get("/api/goals/{goal_id}")
    def get_goal(goal_id: str) -> dict[str, Any]:
        try:
            return goal_response(goal_id)
        except (StorageError, GoalError) as exc:
            raise goal_error(exc) from exc

    @router.patch("/api/goals/{goal_id}")
    def patch_goal(goal_id: str, request: GoalPatchRequest) -> dict[str, Any]:
        fields = request.model_dump(exclude_unset=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update.")
        try:
            container.goals.update(goal_id, DASHBOARD_OWNER, **fields)
            return goal_response(goal_id)
        except (StorageError, GoalError) as exc:
            raise goal_error(exc) from exc

    @router.get("/api/plans")
    def list_plans(
        goal_id: Annotated[str | None, Query(max_length=64)] = None,
    ) -> list[dict[str, Any]]:
        return [plan_payload(p) for p in container.plans.list(DASHBOARD_OWNER, goal_id=goal_id)]

    @router.post("/api/plans", status_code=201)
    def create_plan(request: PlanCreateRequest) -> dict[str, Any]:
        try:
            plan = container.plans.propose(
                DASHBOARD_OWNER,
                request.title,
                [s.model_dump(exclude_none=True) for s in request.steps],
                goal_id=request.goal_id,
            )
        except (StorageError, GoalError) as exc:
            raise goal_error(exc) from exc
        return plan_payload(plan)

    @router.get("/api/plans/{plan_id}")
    def get_plan(plan_id: str) -> dict[str, Any]:
        try:
            return plan_payload(container.plans.get(plan_id, DASHBOARD_OWNER))
        except StorageError as exc:
            raise goal_error(exc) from exc

    @router.post("/api/plans/{plan_id}/approve")
    def approve_plan(plan_id: str) -> dict[str, Any]:
        try:
            return plan_payload(container.plans.approve(plan_id, DASHBOARD_OWNER))
        except StorageError as exc:
            raise goal_error(exc) from exc
        except GoalError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/api/plans/{plan_id}/resume")
    def resume_plan(plan_id: str) -> dict[str, Any]:
        """Continue an approved plan (e.g. after a commit step was approved). Idempotent."""
        try:
            return plan_payload(container.plans.resume(plan_id, DASHBOARD_OWNER))
        except StorageError as exc:
            raise goal_error(exc) from exc
        except GoalError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/api/plans/{plan_id}/cancel")
    def cancel_plan(plan_id: str) -> dict[str, Any]:
        try:
            return plan_payload(container.plans.cancel(plan_id, DASHBOARD_OWNER))
        except StorageError as exc:
            raise goal_error(exc) from exc
        except GoalError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router
