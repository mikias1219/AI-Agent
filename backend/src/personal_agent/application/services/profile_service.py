"""Owner profile use cases — timezone and language preferences."""

from __future__ import annotations

from personal_agent.application.services.task_service import UNSET
from personal_agent.domain.dates import get_zone
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
        self._repository.save(profile)
        return profile

    def save(self, profile: OwnerProfile) -> OwnerProfile:
        self._repository.save(profile)
        return profile
