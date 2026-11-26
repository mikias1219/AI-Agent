"""Projects API (P2-1)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict

from personal_agent.app.container import AppContainer
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectIn(_Strict):
    name: str
    status: str = "active"
    deadline: str | None = None
    notes: str = ""


class ProjectPatch(_Strict):
    name: str | None = None
    status: str | None = None
    deadline: str | None = None
    notes: str | None = None


def build_projects_router(container: AppContainer) -> APIRouter:
    router = APIRouter(prefix="/api/projects", tags=["projects"])
    owner = DASHBOARD_OWNER
    svc = container.projects

    @router.get("")
    def list_projects() -> list[dict[str, Any]]:
        return svc.list(owner)

    @router.post("", status_code=201)
    def create(body: ProjectIn) -> dict[str, Any]:
        return svc.view(owner, svc.create(owner, body.model_dump(exclude_none=True)))

    @router.patch("/{project_id}")
    def patch(project_id: str, body: ProjectPatch) -> dict[str, Any]:
        return svc.view(owner, svc.update(owner, project_id, body.model_dump(exclude_unset=True)))

    @router.delete("/{project_id}", status_code=204)
    def delete(project_id: str) -> Response:
        svc.delete(owner, project_id)
        return Response(status_code=204)

    return router
