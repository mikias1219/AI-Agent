"""Persistence for one local owner; the fixed primary key serializes registration."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import WorkspaceAccount
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import WorkspaceAccountRow


class WorkspaceAccountRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def get(self) -> WorkspaceAccount | None:
        with session_scope(self._factory) as session:
            row = session.get(WorkspaceAccountRow, "owner")
            return WorkspaceAccount(row.name, row.email, row.password_hash) if row else None

    def create(self, account: WorkspaceAccount) -> None:
        try:
            with session_scope(self._factory) as session:
                session.add(
                    WorkspaceAccountRow(
                        id="owner",
                        name=account.name,
                        email=account.email,
                        password_hash=account.password_hash,
                    )
                )
        except IntegrityError as exc:
            raise StorageError("This workspace is already registered. Please log in.") from exc

    def update_password(self, password_hash: str) -> None:
        with session_scope(self._factory) as session:
            row = session.get(WorkspaceAccountRow, "owner")
            if row is None:
                raise StorageError(
                    "No registered account. This password is managed in backend/.env."
                )
            row.password_hash = password_hash
