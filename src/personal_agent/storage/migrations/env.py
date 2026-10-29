"""Alembic environment: resolves URL from settings, binds Base metadata.

Usage:
    alembic revision --autogenerate -m "change"
    alembic upgrade head
"""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import pool

from personal_agent.config import load_settings
from personal_agent.storage.db import create_engine_from_url
from personal_agent.storage.models import Base

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    """DATABASE_URL from the environment wins over configured settings."""
    return os.environ.get("DATABASE_URL") or load_settings().database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB (for review workflows)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the configured database and apply migrations."""
    engine = create_engine_from_url(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
