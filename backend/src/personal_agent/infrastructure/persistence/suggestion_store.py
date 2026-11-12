"""SQLAlchemy-backed suggestion repository (SQLite and Postgres)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.ports import SuggestionRepository
from personal_agent.domain.suggestions import Suggestion
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import SuggestionRow


def _aware(value: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; every stored instant is UTC."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _suggestion(row: SuggestionRow) -> Suggestion:
    return Suggestion(
        id=row.id,
        owner_user_id=row.owner_user_id,
        kind=row.kind,
        title=row.title,
        reason=row.reason or "",
        source=row.source,
        status=row.status,
        proposed_action=dict(row.proposed_action or {}),  # type: ignore[arg-type]
        expires_at=_aware(row.expires_at),
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
        decided_at=_aware(row.decided_at),
        feedback=row.feedback or "",
        outcome=row.outcome or "",
        approval_id=row.approval_id,
    )


def _apply(row: SuggestionRow, suggestion: Suggestion) -> None:
    row.kind = suggestion.kind
    row.title = suggestion.title
    row.reason = suggestion.reason
    row.source = suggestion.source
    row.status = suggestion.status
    row.proposed_action = dict(suggestion.proposed_action)
    row.expires_at = suggestion.expires_at
    row.decided_at = suggestion.decided_at
    row.feedback = suggestion.feedback
    row.outcome = suggestion.outcome
    row.approval_id = suggestion.approval_id
    if suggestion.updated_at is not None:
        row.updated_at = suggestion.updated_at


class SuggestionRepositoryImpl(SuggestionRepository):
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, suggestion: Suggestion) -> None:
        row = SuggestionRow(id=suggestion.id, owner_user_id=suggestion.owner_user_id)
        _apply(row, suggestion)
        if suggestion.created_at is not None:
            row.created_at = suggestion.created_at
        if suggestion.updated_at is None:
            row.updated_at = row.created_at
        with session_scope(self._factory) as session:
            session.add(row)

    def get(self, suggestion_id: str) -> Suggestion | None:
        with session_scope(self._factory) as session:
            row = session.get(SuggestionRow, suggestion_id)
            return _suggestion(row) if row else None

    def save(self, suggestion: Suggestion) -> None:
        with session_scope(self._factory) as session:
            row = session.get(SuggestionRow, suggestion.id)
            if row is None:
                raise StorageError(f"Unknown suggestion '{suggestion.id}'.")
            _apply(row, suggestion)

    def list(
        self,
        owner_user_id: str,
        statuses: Sequence[str] | None = None,
        limit: int = 200,
    ) -> list[Suggestion]:
        with session_scope(self._factory) as session:
            query = session.query(SuggestionRow).filter(
                SuggestionRow.owner_user_id == owner_user_id
            )
            if statuses is not None:
                query = query.filter(SuggestionRow.status.in_(list(statuses)))
            rows = query.order_by(SuggestionRow.created_at.desc(), SuggestionRow.id.desc())
            return [_suggestion(r) for r in rows.limit(limit).all()]
