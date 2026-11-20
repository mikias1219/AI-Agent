"""Agent control, permissions, capabilities, skills and undo (Phase 6 split)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from personal_agent.app.container import AppContainer
from personal_agent.application.security.owner_policy import (
    HARD_CEILING_TOOLS,
    OwnerPermissionPolicy,
)
from personal_agent.domain.exceptions import AgentError, StorageError

DASHBOARD_OWNER = "dashboard"


class AgentControlPatch(BaseModel):
    autonomy_preset: str | None = None
    paused: bool | None = None
    tool_permissions: dict[str, str] | None = None


def build_agent_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["agent"])

    @router.get("/api/agent/skills")
    def list_agent_skills() -> list[dict[str, Any]]:
        from personal_agent.agent import list_skills

        return [
            {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
                "workflow": skill.workflow,
                "tags": list(skill.tags),
                "tool_groups": list(skill.tool_groups),
            }
            for skill in list_skills()
        ]

    @router.get("/api/agent/control")
    def get_agent_control() -> dict[str, Any]:
        return container.agent_control.get(DASHBOARD_OWNER).to_payload()

    @router.patch("/api/agent/control")
    def patch_agent_control(request: AgentControlPatch) -> dict[str, Any]:
        try:
            state = container.agent_control.patch(
                DASHBOARD_OWNER,
                autonomy_preset=request.autonomy_preset,
                paused=request.paused,
                tool_permissions=request.tool_permissions,
                known_tools={spec.name for spec in container.registry.specs()},
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        container.audit.record(
            "agent.control_changed",
            DASHBOARD_OWNER,
            {
                "autonomy_preset": state.autonomy_preset,
                "paused": state.paused,
                "tool_permissions": state.tool_permissions,
            },
        )
        return state.to_payload()

    @router.get("/api/agent/permissions")
    def agent_permissions() -> dict[str, Any]:
        modes = container.agent_control.tool_permissions(DASHBOARD_OWNER)
        policy = OwnerPermissionPolicy(
            modes_of=lambda: modes,
            autonomy_preset_of=lambda: container.agent_control.get(
                DASHBOARD_OWNER
            ).autonomy_preset,
        )
        tools = []
        for spec in sorted(container.registry.specs(), key=lambda item: item.name):
            tools.append(
                {
                    "name": spec.name,
                    "access_kind": spec.access_kind,
                    "description": spec.description,
                    "mode": policy.effective_mode(spec),
                    "ceiling": spec.name in HARD_CEILING_TOOLS
                    or spec.access_kind == "destructive",
                }
            )
        return {"tools": tools}

    @router.get("/api/agent/capabilities")
    def agent_capabilities() -> dict[str, Any]:
        specs = container.registry.specs()
        by_kind: dict[str, list[str]] = {
            "read": [],
            "prepare": [],
            "execute": [],
            "destructive": [],
        }
        for spec in specs:
            by_kind.setdefault(spec.access_kind, []).append(spec.name)
        for names in by_kind.values():
            names.sort()
        return {
            "tools": [
                {
                    "name": spec.name,
                    "access_kind": spec.access_kind,
                    "description": spec.description,
                }
                for spec in sorted(specs, key=lambda item: item.name)
            ],
            "counts": {kind: len(names) for kind, names in by_kind.items()},
        }

    @router.get("/api/undo")
    def list_undo() -> dict[str, Any]:
        return {"items": container.undo.list_open(DASHBOARD_OWNER)}

    @router.post("/api/undo/{undo_id}")
    def apply_undo(undo_id: str) -> dict[str, Any]:
        try:
            result = container.undo.undo(undo_id, DASHBOARD_OWNER)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except AgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"id": result.id, "summary": result.summary, "undone": result.undone}

    return router
