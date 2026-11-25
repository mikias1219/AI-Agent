"""Owner profile use cases — timezone and language preferences."""

from __future__ import annotations

from personal_agent.application.services.task_service import UNSET
from personal_agent.domain.dates import get_zone
from personal_agent.domain.life import BIO_MAX, LifeError, parse_date
from personal_agent.domain.models import OwnerProfile
from personal_agent.domain.ports import OwnerProfileRepository


class ProfileService:
    """Read and update per-owner preferences; unknown owners get defaults (UTC, en)."""

    def __init__(self, repository: OwnerProfileRepository) -> None:
        self._repository = repository

    def get(self, owner_id: str) -> OwnerProfile:
        return self._repository.get(owner_id) or OwnerProfile(owner_id=owner_id)

    def timezone_for(self, owner_id: str) -> str:
        return self.get(owner_id).timezone

    def update(
        self,
        owner_id: str,
        *,
        name: str | None = UNSET,
        timezone: str = UNSET,
        language: str = UNSET,
        bio: str = UNSET,
        birthday: str | None = UNSET,
    ) -> OwnerProfile:
        profile = self.get(owner_id)
        if timezone is not UNSET:
            get_zone(timezone)  # raises ValueError for unknown names
            profile.timezone = timezone
        if language is not UNSET:
            if not language.strip():
                raise ValueError("Language must be a non-empty string.")
            profile.language = language.strip()
        if name is not UNSET:
            profile.name = name.strip() if name and name.strip() else None
        if bio is not UNSET:
            if not isinstance(bio, str) or len(bio.strip()) > BIO_MAX:
                raise ValueError(f"Bio must be at most {BIO_MAX} characters.")
            profile.bio = bio.strip()
        if birthday is not UNSET:
            profile.birthday = None if birthday is None else _check_birthday(birthday)
        self._repository.save(profile)
        return profile

    def save(self, profile: OwnerProfile) -> OwnerProfile:
        self._repository.save(profile)
        return profile


def _check_birthday(value: object) -> str:
    try:
        return parse_date(value, "birthday").isoformat()
    except LifeError as exc:
        raise ValueError(str(exc)) from exc
