"""SQLAlchemy repository for projects."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.life import LifeConflict
from personal_agent.domain.projects import Project
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import ProjectRow


def _project(row: ProjectRow) -> Project:
    created = row.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return Project(
        row.id, row.owner_user_id, row.name, row.status, row.deadline, row.notes or "", created
    )


def _fill(row: ProjectRow, project: Project) -> None:
    row.owner_user_id = project.owner_user_id
    row.name = project.name
    row.status = project.status
    row.deadline = project.deadline
    row.notes = project.notes
    row.created_at = project.created_at or datetime.now(UTC)


class ProjectRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, project: Project) -> None:
        try:
            with session_scope(self._factory) as s:
                row = ProjectRow(id=project.id)
                _fill(row, project)
                s.add(row)
        except IntegrityError as exc:
            raise LifeConflict("A project with that name already exists.") from exc

    def get(self, owner: str, project_id: str) -> Project | None:
        with session_scope(self._factory) as s:
            row = s.get(ProjectRow, project_id)
            return _project(row) if row and row.owner_user_id == owner else None

    def save(self, project: Project) -> None:
        try:
            with session_scope(self._factory) as s:
                row = s.get(ProjectRow, project.id)
                if row is not None:
                    _fill(row, project)
        except IntegrityError as exc:
            raise LifeConflict("A project with that name already exists.") from exc

    def delete(self, owner: str, project_id: str) -> bool:
        with session_scope(self._factory) as s:
            row = s.get(ProjectRow, project_id)
            if row is None or row.owner_user_id != owner:
                return False
            s.delete(row)
            return True

    def list(self, owner: str) -> Sequence[Project]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(ProjectRow)
                .where(ProjectRow.owner_user_id == owner)
                .order_by(ProjectRow.name)
            )
            return [_project(r) for r in rows]
