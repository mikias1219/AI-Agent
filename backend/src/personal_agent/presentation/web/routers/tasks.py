"""Task CRUD (Phase 6 split)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from personal_agent.app.container import AppContainer
from personal_agent.domain.dates import parse_due
from personal_agent.domain.exceptions import AgentError, StorageError
from personal_agent.domain.models import Task, TaskPriority, TaskStatus
from personal_agent.domain.task_rules import TaskView
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER, task_payload


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=10_000)
    notes: str | None = Field(default=None, max_length=10_000)
    priority: TaskPriority = TaskPriority.NONE
    due_at: datetime | None = None
    due: str | None = Field(default=None, max_length=128)
    project: str = Field(default="", max_length=128)
    tags: list[str] = Field(default_factory=list, max_length=20)


class TaskPatchRequest(BaseModel):
    status: TaskStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=10_000)
    notes: str | None = Field(default=None, max_length=10_000)
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    due: str | None = Field(default=None, max_length=128)
    project: str | None = Field(default=None, max_length=128)
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Task title must be a non-empty string.")
        return value


def build_tasks_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["tasks"])

    def due_from(due_at: datetime | None, due: str | None) -> datetime | None:
        timezone = container.profiles.timezone_for(DASHBOARD_OWNER)
        if due is not None and due.strip():
            return parse_due(due, timezone)
        if due_at is not None:
            return parse_due(due_at.isoformat(), timezone)
        return None

    def task_or_404(task_id: str) -> Task:
        task = container.tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        return task

    def task_error(exc: Exception) -> HTTPException:
        missing = isinstance(exc, StorageError) and "unknown task" in str(exc).lower()
        return HTTPException(status_code=404 if missing else 400, detail=str(exc))

    @router.get("/api/tasks")
    def tasks(
        view: Annotated[TaskView | None, Query()] = None,
        status: Annotated[TaskStatus | None, Query()] = None,
        priority: Annotated[TaskPriority | None, Query()] = None,
        project: str | None = Query(default=None, max_length=128),
        tag: str | None = Query(default=None, max_length=64),
        q: str | None = Query(default=None, max_length=256),
        include_deleted: bool = Query(default=False),
    ) -> list[dict[str, Any]]:
        timezone = container.profiles.timezone_for(DASHBOARD_OWNER)
        if q is not None and q.strip():
            found = container.tasks.search(q, include_deleted=include_deleted)
            if status is not None:
                found = [t for t in found if t.status is status]
            if view is not None:
                in_view = {t.id for t in container.tasks.list(status, view=view, timezone=timezone)}
                found = [t for t in found if t.id in in_view]
        else:
            found = container.tasks.list(
                status, view=view, include_deleted=include_deleted, timezone=timezone
            )
        if priority is not None:
            found = [t for t in found if t.priority is priority]
        if project is not None:
            found = [t for t in found if t.project.lower() == project.lower()]
        if tag is not None:
            found = [t for t in found if tag.lower() in (x.lower() for x in t.tags)]
        return [task_payload(task) for task in found]

    @router.post("/api/tasks", status_code=201)
    def create_task(request: TaskCreateRequest) -> dict[str, Any]:
        try:
            task_id = container.tasks.create(
                title=request.title.strip(),
                description=(
                    request.notes if request.notes is not None else request.description
                ).strip(),
                owner_user_id=DASHBOARD_OWNER,
                priority=request.priority,
                due_at=due_from(request.due_at, request.due),
                project=request.project,
                tags=request.tags,
                source="manual",
            )
            task = container.tasks.get(task_id)
        except (AgentError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if task is None:
            raise HTTPException(status_code=500, detail="Created task could not be reloaded.")
        return task_payload(task)

    @router.get("/api/tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, Any]:
        return task_payload(task_or_404(task_id))

    @router.patch("/api/tasks/{task_id}")
    def patch_task(task_id: str, request: TaskPatchRequest) -> dict[str, Any]:
        sent = request.model_fields_set
        try:
            fields: dict[str, Any] = {}
            if request.title is not None:
                fields["title"] = request.title
            notes = request.notes if request.notes is not None else request.description
            if notes is not None:
                fields["description"] = notes
            if request.priority is not None:
                fields["priority"] = request.priority
            if request.project is not None:
                fields["project"] = request.project
            if request.tags is not None:
                fields["tags"] = request.tags
            if sent & {"due_at", "due"}:
                fields["due_at"] = due_from(request.due_at, request.due)
            task_or_404(task_id)
            if request.status is not None:
                container.tasks.advance(task_id, request.status)
            if fields:
                container.tasks.update(task_id, **fields)
        except (AgentError, ValueError) as exc:
            raise task_error(exc) from exc
        return task_payload(task_or_404(task_id))

    @router.post("/api/tasks/{task_id}/reopen")
    def reopen_task(task_id: str) -> dict[str, Any]:
        try:
            container.tasks.reopen(task_id)
        except (AgentError, ValueError) as exc:
            raise task_error(exc) from exc
        return task_payload(task_or_404(task_id))

    @router.delete("/api/tasks/{task_id}")
    def delete_task(task_id: str) -> dict[str, Any]:
        try:
            container.tasks.soft_delete(task_id)
        except (AgentError, ValueError) as exc:
            raise task_error(exc) from exc
        return {"id": task_id, "deleted": True}

    return router