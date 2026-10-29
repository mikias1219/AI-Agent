"""SQLite-backed personal memory (implements `core.ports.MemoryStore`).

Deliberately simple: deduplicated facts (user, kind, content) and recency-ranked
recall — this covers preferences and context from day one. When semantic
retrieval is justified later, it arrives as an additional adapter implementing the
same protocol (e.g. embeddings table + nearest-neighbor recall), not by rewriting
the port or its callers.
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.core.ports import MemoryStore
from personal_agent.storage.db import session_scope
from personal_agent.storage.models import MemoryFactRow

logger = logging.getLogger(__name__)


class SqliteMemoryStore(MemoryStore):
    """Facts store with insert-skip dedup and newest-first recall."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def remember(self, user_id: str, kind: str, content: str) -> None:
        """Persist a fact; duplicates are silently dropped (append-only semantics)."""
        content = content.strip()
        if not content:
            return
        try:
            with session_scope(self._factory) as session:
                session.add(MemoryFactRow(user_id=user_id, kind=kind, content=content))
        except IntegrityError:
            logger.debug("Duplicate fact ignored for kind='%s'.", kind)

    def recall(self, user_id: str, kind: str | None = None, limit: int = 10) -> list[str]:
        """Newest-first facts for the user, optionally filtered by kind."""
        with session_scope(self._factory) as session:
            query = session.query(MemoryFactRow).filter(
                MemoryFactRow.user_id == user_id
            )
            if kind is not None:
                query = query.filter(MemoryFactRow.kind == kind)
            rows = (
                query.order_by(MemoryFactRow.created_at.desc(), MemoryFactRow.id.desc())
                .limit(max(1, limit))
                .all()
            )
        return [row.content for row in rows]


__all__ = ["SqliteMemoryStore"]
