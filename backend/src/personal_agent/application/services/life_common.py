"""Shared helpers for the life services."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.domain.dates import get_zone
from personal_agent.domain.life import LifeError
from personal_agent.domain.ports import AuditLog


class LifeContext:
    """Clock, owner timezone and audit trail shared by every life service."""

    def __init__(
        self,
        profiles: ProfileService,
        *,
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._profiles = profiles
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    def now(self) -> datetime:
        return self._clock()

    def today(self, owner: str) -> date:
        zone = get_zone(self._profiles.timezone_for(owner))
        return self._clock().astimezone(zone).date()

    def local_date(self, owner: str, moment: datetime) -> date:
        return moment.astimezone(get_zone(self._profiles.timezone_for(owner))).date()

    def record(self, event: str, owner: str, **details: object) -> None:
        """Audit ids and counts only, never content."""
        if self._audit is not None:
            self._audit.record(event, owner, dict(details))


def not_found(what: str) -> LifeError:
    from personal_agent.domain.life import LifeNotFound

    return LifeNotFound(f"{what} not found.")
