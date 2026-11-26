"""Projects (P2-1): a named body of work with status, deadline and progress from its tasks."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

PROJECT_STATUSES = ("active", "paused", "done", "archived")
NAME_MAX = 128


@dataclass(slots=True)
class Project:
    id: str
    owner_user_id: str
    name: str
    status: str = "active"
    deadline: date | None = None
    notes: str = ""
    created_at: datetime | None = None


class ProjectRepository(Protocol):
    def add(self, project: Project) -> None: ...
    def get(self, owner: str, project_id: str) -> Project | None: ...
    def save(self, project: Project) -> None: ...
    def delete(self, owner: str, project_id: str) -> bool: ...
    def list(self, owner: str) -> Sequence[Project]: ...
