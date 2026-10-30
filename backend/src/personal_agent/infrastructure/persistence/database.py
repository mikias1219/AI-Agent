"""Database engine and session factory.

`SQLite first, PostgreSQL when justified` is a URL change (`DATABASE_URL`), because
SQLAlchemy 2.0 + Alembic are already in place from day one.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.exceptions import StorageError
from personal_agent.infrastructure.persistence.models import Base

logger = logging.getLogger(__name__)


def create_engine_from_url(database_url: str, **engine_kwargs: Any) -> Engine:
    """Build an Engine for `database_url`, with SQLite thread-safety handled."""
    if not database_url:
        raise StorageError("DATABASE_URL is empty; cannot build a DB engine.")
    if database_url.startswith("sqlite"):
        # Enables CLI tests/threads over one file. Postgres needs no such arg.
        engine_kwargs.setdefault("connect_args", {"check_same_thread": False})
    try:
        parsed = make_url(database_url)
        if (
            parsed.drivername.startswith("sqlite")
            and parsed.database
            and parsed.database != ":memory:"
            and not parsed.database.startswith("file:")
        ):
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(database_url, future=True, **engine_kwargs)
    except Exception as exc:
        raise StorageError(
            f"Could not create database engine for URL: {urlsplit(database_url).scheme}."
        ) from exc


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build the project-standard session factory (commit-on-exit, rollback-on-error)."""
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Unit-of-work pattern used by every repository method."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine) -> None:
    """Create all tables if they are missing.

    Dev/bootstrap convenience only. Migrations (Alembic) are the canonical schema
    history: use `alembic revision --autogenerate` then `alembic upgrade head` once
    the schema starts evolving.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema ensured (%s tables).", len(Base.metadata.tables))
