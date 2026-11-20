"""Workspace export and wipe (Phase 6 split)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer
from personal_agent.domain.exceptions import AgentError

DASHBOARD_OWNER = "dashboard"


class WorkspaceWipeRequest(BaseModel):
    token: str = Field(min_length=8, max_length=256)
    confirm_phrase: str = Field(min_length=1, max_length=64)


def build_workspace_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["workspace"])

    @router.get("/api/export")
    def export_workspace() -> dict[str, Any]:
        return container.workspace_data.export(DASHBOARD_OWNER)

    @router.post("/api/workspace/wipe/token")
    def wipe_workspace_token() -> dict[str, str]:
        return container.workspace_data.issue_wipe_token(DASHBOARD_OWNER)

    @router.post("/api/workspace/wipe")
    def wipe_workspace(request: WorkspaceWipeRequest) -> dict[str, Any]:
        try:
            return container.workspace_data.wipe(
                DASHBOARD_OWNER,
                token=request.token,
                confirm_phrase=request.confirm_phrase,
            )
        except AgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
