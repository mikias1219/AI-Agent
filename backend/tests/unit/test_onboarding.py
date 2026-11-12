"""First-run checklist completes only after real marks."""

from __future__ import annotations

from personal_agent.application.services.onboarding_service import OnboardingService
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.infrastructure.persistence.repositories import OwnerProfileRepositoryImpl


def test_wizard_then_checklist(session_factory) -> None:
    profiles = ProfileService(OwnerProfileRepositoryImpl(session_factory))
    service = OnboardingService(profiles)
    assert service.payload("dashboard")["wizard_completed"] is False

    after = service.complete_wizard("dashboard", name="Mikias", timezone="UTC")
    assert after["wizard_completed"] is True
    assert after["show_checklist"] is True
    assert after["checklist_complete"] is False

    for item in (
        "asked_agent",
        "created_task",
        "approved_action",
        "saved_memory",
        "briefing_ready",
    ):
        assert service.mark("dashboard", item) is True
        assert service.mark("dashboard", item) is False

    done = service.payload("dashboard")
    assert done["checklist_complete"] is True
    assert done["show_checklist"] is False
