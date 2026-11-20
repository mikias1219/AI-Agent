"""Memory endpoints (Phase 6 split)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer
from personal_agent.domain.exceptions import AgentError, StorageError
from personal_agent.domain.memory import Memory, normalize_kind
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER, iso


class MemoryCreateRequest(BaseModel):
    kind: str = Field(default="fact", max_length=32)
    content: str = Field(min_length=1, max_length=2000)
    source_run_id: str | None = Field(default=None, max_length=64)


class MemoryPatchRequest(BaseModel):
    kind: str | None = Field(default=None, max_length=32)
    content: str | None = Field(default=None, min_length=1, max_length=2000)


class MemoryForgetAllRequest(BaseModel):
    token: str = Field(min_length=8, max_length=256)
    confirm_phrase: str = Field(min_length=1, max_length=64)


class MemoryProposalCreateRequest(BaseModel):
    kind: str = Field(default="fact", max_length=32)
    content: str = Field(min_length=1, max_length=2000)
    source_run_id: str | None = Field(default=None, max_length=64)
    source: str = Field(default="", max_length=256)


def build_memory_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["memory"])

    def memory_payload(memory: Memory) -> dict[str, Any]:
        return {
            "id": memory.id,
            "kind": memory.kind,
            "content": memory.content,
            "source_run_id": memory.source_run_id,
            "last_used_at": iso(memory.last_used_at),
            "created_at": iso(memory.created_at),
        }

    def proposal_payload(row: dict[str, str]) -> dict[str, Any]:
        return {
            "id": row.get("id", ""),
            "kind": row.get("kind", "fact"),
            "content": row.get("content", ""),
            "status": row.get("status", "proposed"),
            "source_run_id": row.get("source_run_id") or None,
            "source": row.get("source") or "",
            "created_at": row.get("created_at") or None,
        }

    @router.get("/api/memories")
    def list_memories(
        kind: Annotated[str | None, Query()] = None,
        q: Annotated[str | None, Query(max_length=256)] = None,
    ) -> list[dict[str, Any]]:
        kind_n = None
        if kind is not None:
            try:
                kind_n = normalize_kind(kind)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return [
            memory_payload(m) for m in container.memories.list(DASHBOARD_OWNER, kind=kind_n, q=q)
        ]

    @router.get("/api/memories/proposals")
    def list_memory_proposals() -> list[dict[str, Any]]:
        rows = container.memories.list_proposals(DASHBOARD_OWNER)
        return [proposal_payload(row) for row in rows]

    @router.post("/api/memories/proposals", status_code=201)
    def create_memory_proposal(request: MemoryProposalCreateRequest) -> dict[str, Any]:
        try:
            proposal = container.memories.propose(
                DASHBOARD_OWNER,
                request.kind,
                request.content,
                source_run_id=request.source_run_id,
                source=request.source or "Manual",
            )
        except (AgentError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return proposal_payload(proposal)

    @router.post("/api/memories/proposals/{proposal_id}/confirm", status_code=201)
    def confirm_memory_proposal(proposal_id: str) -> dict[str, Any]:
        try:
            memory = container.memories.confirm_proposal(DASHBOARD_OWNER, proposal_id)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (AgentError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return memory_payload(memory)

    @router.post("/api/memories/proposals/{proposal_id}/dismiss", status_code=204)
    def dismiss_memory_proposal(proposal_id: str) -> Response:
        try:
            container.memories.dismiss_proposal(DASHBOARD_OWNER, proposal_id)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except AgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return Response(status_code=204)

    @router.get("/api/memories/search")
    def search_memories(
        q: Annotated[str, Query(min_length=1, max_length=500)],
    ) -> list[dict[str, Any]]:
        return [memory_payload(m) for m in container.memories.search(DASHBOARD_OWNER, q)]

    @router.post("/api/memories/forget-all/token")
    def forget_all_token() -> dict[str, str]:
        return container.memories.issue_forget_token(DASHBOARD_OWNER)

    @router.post("/api/memories/forget-all")
    def forget_all(request: MemoryForgetAllRequest) -> dict[str, Any]:
        try:
            count = container.memories.forget_all(
                DASHBOARD_OWNER,
                token=request.token,
                confirm_phrase=request.confirm_phrase,
            )
        except AgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"deleted": count}

    @router.post("/api/memories", status_code=201)
    def create_memory(request: MemoryCreateRequest) -> dict[str, Any]:
        try:
            memory = container.memories.create(
                DASHBOARD_OWNER,
                request.kind,
                request.content,
                source_run_id=request.source_run_id,
                actor=DASHBOARD_OWNER,
            )
        except (AgentError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return memory_payload(memory)

    @router.get("/api/memories/{memory_id}")
    def get_memory(memory_id: str) -> dict[str, Any]:
        memory = container.memories.get(memory_id)
        if memory is None or memory.user_id != DASHBOARD_OWNER:
            raise HTTPException(status_code=404, detail="Memory not found.")
        return memory_payload(memory)

    @router.patch("/api/memories/{memory_id}")
    def patch_memory(memory_id: str, request: MemoryPatchRequest) -> dict[str, Any]:
        fields: dict[str, str] = {}
        if request.content is not None:
            fields["content"] = request.content
        if request.kind is not None:
            fields["kind"] = request.kind
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update.")
        try:
            memory = container.memories.update(memory_id, DASHBOARD_OWNER, **fields)
        except (StorageError, AgentError, ValueError) as exc:
            status = 404 if isinstance(exc, StorageError) else 400
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return memory_payload(memory)

    @router.delete("/api/memories/{memory_id}", status_code=204)
    def delete_memory(memory_id: str) -> Response:
        try:
            container.memories.delete(memory_id, DASHBOARD_OWNER)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return Response(status_code=204)

    return router