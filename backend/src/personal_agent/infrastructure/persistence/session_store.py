"""Server-side dashboard sessions (S1): revocable, expiring, sliding."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import UserSessionRow

SHORT_LIFETIME = timedelta(hours=12)
REMEMBER_LIFETIME = timedelta(days=30)
TOUCH_EVERY = timedelta(minutes=10)  # throttle writes for the sliding window


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class SessionStoreImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create(self, session_id: str, owner: str, *, remember: bool, now: datetime) -> datetime:
        lifetime = REMEMBER_LIFETIME if remember else SHORT_LIFETIME
        expires = now + lifetime
        with session_scope(self._factory) as s:
            s.execute(delete(UserSessionRow).where(UserSessionRow.expires_at < now))
            s.add(
                UserSessionRow(
                    id=session_id,
                    owner_user_id=owner,
                    created_at=now,
                    last_seen_at=now,
                    expires_at=expires,
                )
            )
        return expires

    def is_active(self, session_id: str, now: datetime) -> bool:
        """True for a live, unrevoked session; slides the expiry of long (remember) sessions."""
        with session_scope(self._factory) as s:
            row = s.scalars(select(UserSessionRow).where(UserSessionRow.id == session_id)).first()
            if row is None or row.revoked_at is not None or _aware(row.expires_at) <= now:
                return False
            if now - _aware(row.last_seen_at) >= TOUCH_EVERY:
                lifetime = _aware(row.expires_at) - _aware(row.created_at)
                row.last_seen_at = now
                if lifetime > SHORT_LIFETIME:
                    row.expires_at = now + REMEMBER_LIFETIME
            return True

    def revoke(self, session_id: str, now: datetime) -> bool:
        with session_scope(self._factory) as s:
            result = s.execute(
                update(UserSessionRow)
                .where(UserSessionRow.id == session_id, UserSessionRow.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            return bool(result.rowcount)  # type: ignore[attr-defined]

    def revoke_all(self, owner: str, now: datetime) -> int:
        with session_scope(self._factory) as s:
            result = s.execute(
                update(UserSessionRow)
                .where(UserSessionRow.owner_user_id == owner, UserSessionRow.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            return int(result.rowcount or 0)  # type: ignore[attr-defined]
