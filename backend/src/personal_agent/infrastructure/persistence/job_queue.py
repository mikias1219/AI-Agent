"""SQLAlchemy JobQueue (AUT-01)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.scheduler import Job, JobStatus
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import JobRow


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _to_domain(row: JobRow) -> Job:
    return Job(
        id=row.id,
        run_at=_aware(row.run_at) or row.run_at,
        kind=row.kind,
        payload=dict(row.payload or {}),
        status=JobStatus(row.status),
        attempts=row.attempts,
        last_error=row.last_error or "",
        idempotency_key=row.idempotency_key,
        created_at=_aware(row.created_at),
        finished_at=_aware(row.finished_at),
    )


class SqlJobQueue:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def enqueue(self, job: Job) -> Job:
        if not job.idempotency_key:
            raise ValueError("idempotency_key is required")
        existing = self.get_by_key(job.idempotency_key)
        if existing is not None:
            return existing
        job_id = job.id or uuid.uuid4().hex
        row = JobRow(
            id=job_id,
            run_at=job.run_at,
            kind=job.kind,
            payload=dict(job.payload or {}),
            status=JobStatus.PENDING.value,
            attempts=0,
            last_error="",
            idempotency_key=job.idempotency_key,
            created_at=_now(),
        )
        try:
            with session_scope(self._factory) as session:
                session.add(row)
        except IntegrityError:
            found = self.get_by_key(job.idempotency_key)
            if found is not None:
                return found
            raise
        return _to_domain(row)

    def claim_due(self, now: datetime, *, limit: int = 20) -> list[Job]:
        claimed: list[Job] = []
        with session_scope(self._factory) as session:
            query = (
                session.query(JobRow)
                .filter(JobRow.status == JobStatus.PENDING.value, JobRow.run_at <= now)
                .order_by(JobRow.run_at.asc())
                .limit(max(1, limit))
            )
            bind = session.get_bind()
            if bind.dialect.name != "sqlite":
                query = query.with_for_update(skip_locked=True)
            rows = query.all()
            for row in rows:
                row.status = JobStatus.RUNNING.value
                row.attempts = int(row.attempts or 0) + 1
                claimed.append(_to_domain(row))
        return claimed

    def mark_done(self, job_id: str, *, now: datetime) -> None:
        with session_scope(self._factory) as session:
            row = session.get(JobRow, job_id)
            if row is None:
                return
            row.status = JobStatus.DONE.value
            row.finished_at = now
            row.last_error = ""

    def mark_failed(
        self,
        job_id: str,
        *,
        error: str,
        now: datetime,
        retry_at: datetime | None,
    ) -> None:
        with session_scope(self._factory) as session:
            row = session.get(JobRow, job_id)
            if row is None:
                return
            row.last_error = error[:2000]
            if retry_at is not None and (row.attempts or 0) < 5:
                row.status = JobStatus.PENDING.value
                row.run_at = retry_at
                row.finished_at = None
            else:
                row.status = JobStatus.FAILED.value
                row.finished_at = now

    def get_by_key(self, idempotency_key: str) -> Job | None:
        with session_scope(self._factory) as session:
            row = session.query(JobRow).filter(JobRow.idempotency_key == idempotency_key).first()
            return _to_domain(row) if row else None


__all__ = ["SqlJobQueue"]
