"""Google Drive and Calendar sync endpoints (docs/LIFE_API_CONTRACT.md sections 8-9).

A run goes through the tool registry: with mode `ask` it creates one approval and answers
`awaiting_approval`; with mode `auto` it runs. Missing connection or scope is a 409.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from personal_agent.app.container import AppContainer
from personal_agent.domain.life import LifeError
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER

JsonBody = Annotated[dict[str, Any] | None, Body()]


def build_sync_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["sync"])
    owner = DASHBOARD_OWNER

    # -- Drive -----------------------------------------------------------------------

    @router.get("/api/drive-sync/status")
    def drive_status() -> dict[str, Any]:
        return container.drive_sync.status(owner)

    @router.patch("/api/drive-sync/settings")
    def drive_settings(body: JsonBody = None) -> dict[str, Any]:
        data = body or {}
        return container.drive_sync.update_settings(
            owner, enabled=data.get("enabled"), include=data.get("include")
        )

    @router.post("/api/drive-sync/run")
    def drive_run() -> dict[str, Any]:
        return container.drive_sync.request_push(owner, origin="dashboard")

    @router.get("/api/drive-sync/items")
    def drive_items(
        object_type: str = "",
        limit: Annotated[int | None, Query()] = None,
        offset: Annotated[int | None, Query()] = None,
    ) -> list[dict[str, Any]]:
        return container.drive_sync.items(
            owner,
            object_type=object_type or None,
            limit=50 if limit is None else limit,
            offset=0 if offset is None else offset,
        )

    # -- Calendar --------------------------------------------------------------------

    @router.get("/api/calendar-sync/status")
    def calendar_status() -> dict[str, Any]:
        return container.calendar_sync.status(owner)

    @router.patch("/api/calendar-sync/settings")
    def calendar_settings(body: JsonBody = None) -> dict[str, Any]:
        return container.calendar_sync.update_settings(owner, enabled=(body or {}).get("enabled"))

    @router.post("/api/calendar-sync/run")
    def calendar_run(body: JsonBody = None) -> dict[str, Any]:
        all_day = (body or {}).get("all_day", False)
        if not isinstance(all_day, bool):
            raise LifeError("all_day must be true or false.")
        return container.calendar_sync.request_run(owner, origin="dashboard", all_day=all_day)

    return router
