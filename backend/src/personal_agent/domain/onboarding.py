"""First-run wizard and getting-started checklist (UX-02)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ChecklistItem = Literal[
    "asked_agent",
    "created_task",
    "approved_action",
    "saved_memory",
    "briefing_ready",
]

CHECKLIST_ITEMS: tuple[ChecklistItem, ...] = (
    "asked_agent",
    "created_task",
    "approved_action",
    "saved_memory",
    "briefing_ready",
)

CHECKLIST_LABELS: dict[ChecklistItem, str] = {
    "asked_agent": "Ask AURA something",
    "created_task": "Create a task",
    "approved_action": "Approve a drafted action",
    "saved_memory": "Save a memory",
    "briefing_ready": "Set up daily briefing (or skip)",
}


@dataclass(slots=True)
class OnboardingState:
    """Persisted first-run progress for one owner."""

    wizard_completed: bool = False
    checklist: dict[str, bool] = field(default_factory=dict)

    def is_done(self, item: ChecklistItem) -> bool:
        return bool(self.checklist.get(item))

    def all_complete(self) -> bool:
        return all(self.is_done(item) for item in CHECKLIST_ITEMS)

    def mark(self, item: ChecklistItem) -> bool:
        """Return True if this call newly completed the item."""
        if self.checklist.get(item):
            return False
        self.checklist[item] = True
        return True


__all__ = [
    "CHECKLIST_ITEMS",
    "CHECKLIST_LABELS",
    "ChecklistItem",
    "OnboardingState",
]
