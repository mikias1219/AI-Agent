"""Time tracking API (P2-2)."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, ConfigDict

from personal_agent.app.container import AppContainer
from personal_agent.application.services.day_service import parse_day
from personal_agent.application.services.time_service import entry_payload
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartIn(_Strict):
    task_id: str | None = None
    project: str = ""
    goal_id: str | None = None
    note: str = ""


class ManualIn(_Strict):
    minutes: int
    day: str | None = None
    task_id: str | None = None
    project: str = ""
    goal_id: str | None = None
    note: str = ""


def build_time_router(container: AppContainer) -> APIRouter:
    router = APIRouter(prefix="/api/time", tags=["time"])
    owner = DASHBOARD_OWNER
    svc = container.time

    def window(from_date: str | None, to_date: str | None) -> tuple[Any, Any]:
        today = container.life_ctx.today(owner)
        end = parse_day(to_date, "to") if to_date else today
        start = parse_day(from_date, "from") if from_date else end - timedelta(days=6)
        return start, end

    @router.get("/running")
    def running() -> dict[str, Any]:
        entry = svc.running(owner)
        return {"entry": entry_payload(entry, container.life_ctx.now()) if entry else None}

    @router.post("/start", status_code=201)
    def start(body: StartIn) -> dict[str, Any]:
        entry = svc.start(owner, **body.model_dump())
        return entry_payload(entry, container.life_ctx.now())

    @router.post("/stop")
    def stop() -> dict[str, Any]:
        return entry_payload(svc.stop(owner), container.life_ctx.now())

    @router.post("/entries", status_code=201)
    def manual(body: ManualIn) -> dict[str, Any]:
        entry = svc.add_manual(owner, body.model_dump(exclude_none=True))
        return entry_payload(entry, container.life_ctx.now())

    @router.get("/entries")
    def entries(
        from_date: Annotated[str | None, Query(alias="from")] = None,
        to_date: Annotated[str | None, Query(alias="to")] = None,
    ) -> list[dict[str, Any]]:
        start_day, end_day = window(from_date, to_date)
        return svc.entries(owner, start_day, end_day)

    @router.delete("/entries/{entry_id}", status_code=204)
    def delete_entry(entry_id: str) -> Response:
        svc.delete(owner, entry_id)
        return Response(status_code=204)

    @router.get("/summary")
    def summary(
        from_date: Annotated[str | None, Query(alias="from")] = None,
        to_date: Annotated[str | None, Query(alias="to")] = None,
    ) -> dict[str, Any]:
        start_day, end_day = window(from_date, to_date)
        return svc.summary(owner, start_day, end_day)

    return router
