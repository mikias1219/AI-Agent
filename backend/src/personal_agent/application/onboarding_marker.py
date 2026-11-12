"""Shared typing for optional onboarding checklist hooks."""

from __future__ import annotations

from typing import Protocol


class OnboardingMarker(Protocol):
    def mark(self, user_id: str, item: str) -> None: ...
