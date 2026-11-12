"""First-run wizard and checklist progress (UX-02)."""

from __future__ import annotations

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.domain.onboarding import (
    CHECKLIST_ITEMS,
    CHECKLIST_LABELS,
    ChecklistItem,
    OnboardingState,
)
from personal_agent.domain.ports import AuditLog


class OnboardingService:
    """Owner-facing onboarding; checklist items complete only after real actions."""

    def __init__(self, profiles: ProfileService, *, audit: AuditLog | None = None) -> None:
        self._profiles = profiles
        self._audit = audit

    def state(self, owner_id: str) -> OnboardingState:
        profile = self._profiles.get(owner_id)
        return OnboardingState(
            wizard_completed=profile.wizard_completed,
            checklist=dict(profile.checklist or {}),
        )

    def payload(self, owner_id: str) -> dict[str, object]:
        state = self.state(owner_id)
        items = [
            {
                "id": item,
                "label": CHECKLIST_LABELS[item],
                "done": state.is_done(item),
            }
            for item in CHECKLIST_ITEMS
        ]
        return {
            "wizard_completed": state.wizard_completed,
            "checklist_complete": state.all_complete(),
            "items": items,
            "show_checklist": state.wizard_completed and not state.all_complete(),
        }

    def complete_wizard(
        self, owner_id: str, *, name: str | None = None, timezone: str | None = None
    ) -> dict[str, object]:
        kwargs: dict[str, object] = {}
        if name is not None:
            kwargs["name"] = name
        if timezone is not None:
            kwargs["timezone"] = timezone
        if kwargs:
            self._profiles.update(owner_id, **kwargs)  # type: ignore[arg-type]
        profile = self._profiles.get(owner_id)
        profile.wizard_completed = True
        self._profiles.save(profile)
        if self._audit:
            self._audit.record("onboarding.wizard_completed", owner_id, {})
        return self.payload(owner_id)

    def mark(self, owner_id: str, item: ChecklistItem) -> bool:
        profile = self._profiles.get(owner_id)
        state = OnboardingState(
            wizard_completed=profile.wizard_completed,
            checklist=dict(profile.checklist or {}),
        )
        if not state.mark(item):
            return False
        profile.checklist = dict(state.checklist)
        self._profiles.save(profile)
        if self._audit:
            self._audit.record("onboarding.checklist_item", owner_id, {"item": item})
        return True

    def skip_briefing(self, owner_id: str) -> dict[str, object]:
        self.mark(owner_id, "briefing_ready")
        return self.payload(owner_id)


__all__ = ["OnboardingService"]
