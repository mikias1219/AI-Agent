"""SQLite/Postgres-backed personal memory with hybrid recall (MEM-04)."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.memory import Memory, MemoryKind, assert_storable, normalize_kind
from personal_agent.domain.ports import EmbeddingProvider, MemoryStore
from personal_agent.infrastructure.embeddings.local import LocalHashEmbeddingProvider, cosine
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import MemoryRow

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_DEFAULT_LIMIT = 8
_W_RECENCY = 0.35
_W_KEYWORD = 0.35
_W_VECTOR = 0.30


def _now() -> datetime:
    return datetime.now(UTC)


def _to_domain(row: MemoryRow) -> Memory:
    return Memory(
        id=row.id,
        user_id=row.user_id,
        kind=row.kind,  # type: ignore[arg-type]
        content=row.content,
        source_run_id=row.source_run_id,
        last_used_at=row.last_used_at,
        created_at=row.created_at,
        deleted_at=row.deleted_at,
    )


class SqliteMemoryStore(MemoryStore):
    """Hybrid memory store: recency + keyword + vector, top 8 by default."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        *,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self._factory = factory
        self._embeddings = embeddings or LocalHashEmbeddingProvider()
        self._fts_ready = False

    def remember(
        self,
        user_id: str,
        kind: str,
        content: str,
        *,
        source_run_id: str | None = None,
    ) -> Memory | None:
        content = assert_storable(content)
        kind_n = normalize_kind(kind)
        existing = self._find_active(user_id, kind_n, content)
        if existing is not None:
            return existing
        memory_id = uuid.uuid4().hex
        embedding = self._embeddings.embed(content)
        row = MemoryRow(
            id=memory_id,
            user_id=user_id,
            kind=kind_n,
            content=content,
            source_run_id=source_run_id,
            embedding=embedding,
            created_at=_now(),
        )
        try:
            with session_scope(self._factory) as session:
                session.add(row)
                self._fts_upsert(session, memory_id, content)
        except IntegrityError:
            logger.debug("Duplicate memory ignored for kind='%s'.", kind_n)
            return self._find_active(user_id, kind_n, content)
        return _to_domain(row)

    def recall(
        self,
        user_id: str,
        kind: str | None = None,
        limit: int = _DEFAULT_LIMIT,
        query: str | None = None,
    ) -> list[str]:
        found = self.search(user_id, query or "", kind=kind, limit=limit)
        if found:
            self.mark_used([m.id for m in found])
        return [m.content for m in found]

    def get(self, memory_id: str) -> Memory | None:
        with session_scope(self._factory) as session:
            row = session.get(MemoryRow, memory_id)
            if row is None or row.deleted_at is not None:
                return None
            return _to_domain(row)

    def list(
        self,
        user_id: str,
        *,
        kind: MemoryKind | None = None,
        q: str | None = None,
        limit: int = 100,
    ) -> list[Memory]:
        with session_scope(self._factory) as session:
            query = session.query(MemoryRow).filter(
                MemoryRow.user_id == user_id,
                MemoryRow.deleted_at.is_(None),
            )
            if kind is not None:
                query = query.filter(MemoryRow.kind == kind)
            if q and q.strip():
                needle = f"%{q.strip().lower()}%"
                query = query.filter(MemoryRow.content.ilike(needle))
            rows = (
                query.order_by(MemoryRow.created_at.desc(), MemoryRow.id.desc())
                .limit(max(1, limit))
                .all()
            )
            return [_to_domain(row) for row in rows]

    def update(self, memory_id: str, *, content: str | None = None, kind: str | None = None) -> Memory:
        with session_scope(self._factory) as session:
            row = session.get(MemoryRow, memory_id)
            if row is None or row.deleted_at is not None:
                raise StorageError(f"Unknown memory '{memory_id}'.")
            if content is not None:
                row.content = assert_storable(content)
                row.embedding = self._embeddings.embed(row.content)
                self._fts_upsert(session, row.id, row.content)
            if kind is not None:
                row.kind = normalize_kind(kind)
            session.flush()
            return _to_domain(row)

    def soft_delete(self, memory_id: str) -> None:
        """Permanent delete (BR-08). Method name kept for the port; row is removed."""
        with session_scope(self._factory) as session:
            row = session.get(MemoryRow, memory_id)
            if row is None or row.deleted_at is not None:
                raise StorageError(f"Unknown memory '{memory_id}'.")
            self._fts_delete(session, memory_id)
            session.delete(row)

    def forget_all(self, user_id: str) -> int:
        with session_scope(self._factory) as session:
            rows = session.query(MemoryRow).filter(MemoryRow.user_id == user_id).all()
            count = len(rows)
            for row in rows:
                self._fts_delete(session, row.id)
                session.delete(row)
            return count

    def search(
        self,
        user_id: str,
        query: str,
        *,
        kind: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[Memory]:
        cap = max(1, min(8, limit))  # MEM-04: at most 8 per run
        with session_scope(self._factory) as session:
            q = session.query(MemoryRow).filter(
                MemoryRow.user_id == user_id,
                MemoryRow.deleted_at.is_(None),
            )
            if kind is not None:
                q = q.filter(MemoryRow.kind == normalize_kind(kind))
            rows = q.all()
            if not rows:
                return []
            query_vec = self._embeddings.embed(query) if query.strip() else None
            keyword_hits = self._keyword_ids(session, query) if query.strip() else set()
            now = _now().timestamp()
            scored: list[tuple[float, MemoryRow]] = []
            for row in rows:
                created = row.created_at.timestamp() if row.created_at else now
                age_days = max(0.0, (now - created) / 86400.0)
                recency = 1.0 / (1.0 + age_days)
                tokens_q = set(_TOKEN.findall(query.lower())) if query.strip() else set()
                tokens_c = set(_TOKEN.findall(row.content.lower()))
                overlap = (
                    len(tokens_q & tokens_c) / max(1, len(tokens_q)) if tokens_q else 0.0
                )
                if row.id in keyword_hits:
                    overlap = max(overlap, 0.85)
                vector = 0.0
                if query_vec and row.embedding:
                    vector = max(0.0, cosine(query_vec, list(row.embedding)))
                # No query → pure recency (plus slight last_used boost).
                if not query.strip():
                    used = row.last_used_at.timestamp() if row.last_used_at else 0.0
                    score = recency + 0.05 * (1.0 / (1.0 + max(0.0, (now - used) / 86400.0)))
                else:
                    score = _W_RECENCY * recency + _W_KEYWORD * overlap + _W_VECTOR * vector
                scored.append((score, row))
            scored.sort(key=lambda item: (-item[0], -(item[1].created_at.timestamp() if item[1].created_at else 0)))
            return [_to_domain(row) for _, row in scored[:cap]]

    def mark_used(self, memory_ids: list[str] | tuple[str, ...]) -> None:
        if not memory_ids:
            return
        stamp = _now()
        with session_scope(self._factory) as session:
            for memory_id in memory_ids:
                row = session.get(MemoryRow, memory_id)
                if row is not None and row.deleted_at is None:
                    row.last_used_at = stamp

    def _find_active(self, user_id: str, kind: str, content: str) -> Memory | None:
        with session_scope(self._factory) as session:
            row = (
                session.query(MemoryRow)
                .filter(
                    MemoryRow.user_id == user_id,
                    MemoryRow.kind == kind,
                    MemoryRow.content == content,
                    MemoryRow.deleted_at.is_(None),
                )
                .first()
            )
            return _to_domain(row) if row else None

    def _ensure_fts(self, session: Session) -> None:
        if self._fts_ready:
            return
        bind = session.get_bind()
        if bind.dialect.name != "sqlite":
            self._fts_ready = True
            return
        session.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts "
                "USING fts5(memory_id UNINDEXED, content, tokenize='porter')"
            )
        )
        self._fts_ready = True

    def _fts_upsert(self, session: Session, memory_id: str, content: str) -> None:
        self._ensure_fts(session)
        bind = session.get_bind()
        if bind.dialect.name != "sqlite":
            return
        session.execute(text("DELETE FROM memory_fts WHERE memory_id = :id"), {"id": memory_id})
        session.execute(
            text("INSERT INTO memory_fts(memory_id, content) VALUES (:id, :content)"),
            {"id": memory_id, "content": content},
        )

    def _fts_delete(self, session: Session, memory_id: str) -> None:
        self._ensure_fts(session)
        bind = session.get_bind()
        if bind.dialect.name != "sqlite":
            return
        session.execute(text("DELETE FROM memory_fts WHERE memory_id = :id"), {"id": memory_id})

    def _keyword_ids(self, session: Session, query: str) -> set[str]:
        self._ensure_fts(session)
        bind = session.get_bind()
        if bind.dialect.name != "sqlite":
            return set()
        tokens = _TOKEN.findall(query.lower())
        if not tokens:
            return set()
        # FTS5 query: OR of token prefixes; escape quotes.
        parts = [f'"{t}"*' for t in tokens[:12]]
        fts_q = " OR ".join(parts)
        try:
            rows = session.execute(
                text("SELECT memory_id FROM memory_fts WHERE memory_fts MATCH :q"),
                {"q": fts_q},
            ).fetchall()
            return {r[0] for r in rows}
        except Exception:  # noqa: BLE001 — FTS may be unavailable; fall back to overlap
            logger.debug("FTS search failed; using token overlap only.", exc_info=True)
            return set()


__all__ = ["SqliteMemoryStore"]
