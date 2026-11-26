"""Habits API (P1-2): CRUD, today row, check-ins, grid. Unknown fields are rejected (422)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from personal_agent.app.container import AppContainer
from personal_agent.application.services.day_service import parse_day
from personal_agent.application.services.habit_service import habit_payload
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleIn(_Strict):
    freq: str
    interval: int = 1
    weekdays: list[int] = Field(default_factory=list)
    day_of_month: int | None = None
    start: str | None = None
    end: str | None = None


class HabitCreate(_Strict):
    name: str
    kind: str = "habit"
    rule: RuleIn | None = None
    target_value: float | None = None
    target_unit: str = ""
    icon: str = ""
    counts_toward_score: bool = True


class HabitPatch(_Strict):
    name: str | None = None
    kind: str | None = None
    rule: RuleIn | None = None
    target_value: float | None = None
    target_unit: str | None = None
    icon: str | None = None
    archived: bool | None = None
    counts_toward_score: bool | None = None


class CheckinIn(_Strict):
    day: str | None = None
    status: str = "done"
    value: float | None = None
    note: str = ""


def build_habits_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["habits"])
    owner = DASHBOARD_OWNER

    @router.get("/api/habits")
    def list_habits() -> list[dict[str, Any]]:
        return container.habits.with_streaks(owner)

    @router.post("/api/habits", status_code=201)
    def create_habit(body: HabitCreate) -> dict[str, Any]:
        data = body.model_dump(exclude_none=True)
        return habit_payload(container.habits.create(owner, data))

    # Fixed paths before `/{habit_id}`.
    @router.get("/api/habits/today")
    def habits_today(day: Annotated[str | None, Query()] = None) -> dict[str, Any]:
        return container.habits.day_status(owner, parse_day(day) if day else None)

    @router.get("/api/habits/grid")
    def habits_grid(days: Annotated[int, Query(ge=1, le=60)] = 7) -> dict[str, Any]:
        return container.habits.grid(owner, days=days)

    @router.patch("/api/habits/{habit_id}")
    def patch_habit(habit_id: str, body: HabitPatch) -> dict[str, Any]:
        data = body.model_dump(exclude_unset=True)
        return habit_payload(container.habits.update(owner, habit_id, data))

    @router.delete("/api/habits/{habit_id}", status_code=204)
    def archive_habit(habit_id: str) -> Response:
        container.habits.archive(owner, habit_id)
        return Response(status_code=204)

    @router.post("/api/habits/{habit_id}/checkins", status_code=201)
    def check_in(habit_id: str, body: CheckinIn) -> dict[str, Any]:
        item = container.habits.check_in(
            owner,
            habit_id,
            day=parse_day(body.day) if body.day else None,
            status=body.status,
            value=body.value,
            note=body.note,
        )
        return {
            "id": item.id,
            "habit_id": item.habit_id,
            "day": item.day.isoformat(),
            "status": item.status,
            "value": item.value,
            "note": item.note,
        }

    @router.delete("/api/habits/{habit_id}/checkins/{day}", status_code=204)
    def undo_check_in(habit_id: str, day: str) -> Response:
        container.habits.undo_check_in(owner, habit_id, parse_day(day))
        return Response(status_code=204)

    return router
