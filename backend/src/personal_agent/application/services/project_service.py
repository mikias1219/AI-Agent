"""Projects: CRUD plus progress computed from the tasks that carry the project name."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any

from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.life import LifeError
from personal_agent.domain.models import TaskStatus
from personal_agent.domain.projects import NAME_MAX, PROJECT_STATUSES, Project, ProjectRepository
from personal_agent.domain.task_rules import effective_day

_FIELDS = {"name", "status", "deadline", "notes"}


class ProjectService:
    def __init__(self, repository: ProjectRepository, ctx: LifeContext, tasks: TaskService) -> None:
        self._repo = repository
        self._ctx = ctx
        self._tasks = tasks

    @staticmethod
    def _name(value: Any) -> str:
        name = str(value or "").strip()
        if not name:
            raise LifeError("Project name is required.")
        if len(name) > NAME_MAX:
            raise LifeError(f"Project name must be at most {NAME_MAX} characters.")
        return name

    @staticmethod
    def _deadline(value: Any) -> date | None:
        if value in (None, ""):
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise LifeError("deadline must be YYYY-MM-DD.") from exc

    def create(self, owner: str, data: Mapping[str, Any]) -> Project:
        unknown = set(data) - _FIELDS
        if unknown:
            raise LifeError(f"Unknown field(s): {', '.join(sorted(unknown))}.")
        status = str(data.get("status") or "active")
        if status not in PROJECT_STATUSES:
            raise LifeError(f"status must be one of: {', '.join(PROJECT_STATUSES)}.")
        project = Project(
            uuid.uuid4().hex,
            owner,
            self._name(data.get("name")),
            status,
            self._deadline(data.get("deadline")),
            str(data.get("notes") or "").strip()[:1000],
            self._ctx.now(),
        )
        self._repo.add(project)
        self._ctx.record("project.created", owner, project_id=project.id)
        return project

    def get(self, owner: str, project_id: str) -> Project:
        project = self._repo.get(owner, project_id)
        if project is None:
            raise not_found("Project")
        return project

    def update(self, owner: str, project_id: str, data: Mapping[str, Any]) -> Project:
        unknown = set(data) - _FIELDS
        if unknown:
            raise LifeError(f"Unknown field(s): {', '.join(sorted(unknown))}.")
        project = self.get(owner, project_id)
        if "name" in data:
            renamed = self._name(data["name"])
            if renamed != project.name:
                for task in self._tasks.list(owner_user_id=owner):
                    if task.project == project.name:
                        self._tasks.update(task.id, project=renamed)
                project.name = renamed
        if "status" in data:
            if data["status"] not in PROJECT_STATUSES:
                raise LifeError(f"status must be one of: {', '.join(PROJECT_STATUSES)}.")
            project.status = data["status"]
        if "deadline" in data:
            project.deadline = self._deadline(data["deadline"])
        if "notes" in data:
            project.notes = str(data["notes"] or "").strip()[:1000]
        self._repo.save(project)
        return project

    def delete(self, owner: str, project_id: str) -> None:
        """Removes the project; its tasks keep their text label and are not deleted."""
        if not self._repo.delete(owner, project_id):
            raise not_found("Project")

    def view(self, owner: str, project: Project) -> dict[str, Any]:
        today = self._ctx.today(owner)
        zone = self._ctx._profiles.timezone_for(owner)  # noqa: SLF001
        done = open_count = overdue = 0
        for task in self._tasks.list(owner_user_id=owner):
            if task.project != project.name:
                continue
            if task.status is TaskStatus.CANCELLED:
                continue
            if task.status is TaskStatus.DONE:
                done += 1
            else:
                open_count += 1
                day = effective_day(task, zone)
                if day is not None and day < today:
                    overdue += 1
        total = done + open_count
        return {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "deadline": project.deadline.isoformat() if project.deadline else None,
            "notes": project.notes,
            "tasks": {"done": done, "open": open_count, "overdue": overdue, "total": total},
            "progress_pct": round(done / total * 100) if total else 0,
            "days_left": (project.deadline - today).days if project.deadline else None,
        }

    def list(self, owner: str) -> list[dict[str, Any]]:
        return [self.view(owner, p) for p in self._repo.list(owner)]
