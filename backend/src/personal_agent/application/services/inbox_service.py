"""Unified inbox (spec §8): approvals and suggestions as one list ordered by urgency.

`open` is what needs the owner now (most urgent first); `done` is what was decided or lapsed
(most recent first). The count is the real number of open items, not a capped list length.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from personal_agent.application.inbox_items import approval_item, suggestion_item
from personal_agent.application.services.approval_service import ApprovalService
from personal_agent.application.services.suggestion_service import SuggestionService
from personal_agent.domain.approvals import ApprovalStatus
from personal_agent.domain.suggestions import urgency_sort_key

OPEN_LIMIT = 200
DONE_LIMIT = 100


class InboxService:
    def __init__(
        self,
        *,
        approvals: ApprovalService,
        suggestions: SuggestionService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._approvals = approvals
        self._suggestions = suggestions
        self._clock = clock or (lambda: datetime.now(UTC))

    def open_items(self, owner_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        now = self._clock()
        items = [
            approval_item(a, now)
            for a in self._approvals.list_approvals(ApprovalStatus.PENDING, limit=OPEN_LIMIT)
            if not a.is_expired(now)
        ]
        items += [suggestion_item(s, now) for s in self._suggestions.open(owner_id)]
        items.sort(key=lambda i: _urgency_key(i))
        return items if limit is None else items[:limit]

    def done_items(self, owner_id: str) -> list[dict[str, Any]]:
        now = self._clock()
        items = [
            approval_item(a, now)
            for a in self._approvals.list_approvals(None, limit=OPEN_LIMIT)
            if a.status is not ApprovalStatus.PENDING or a.is_expired(now)
        ]
        items += [suggestion_item(s, now) for s in self._suggestions.done(owner_id, DONE_LIMIT)]
        items.sort(
            key=lambda i: str(i.get("decided_at") or i.get("created_at") or ""), reverse=True
        )
        return items[:DONE_LIMIT]

    def open_count(self, owner_id: str) -> int:
        return len(self.open_items(owner_id))

    def build(self, owner_id: str, tab: str = "open") -> dict[str, Any]:
        items = self.open_items(owner_id) if tab == "open" else self.done_items(owner_id)
        open_count = len(items) if tab == "open" else self.open_count(owner_id)
        return {"tab": tab, "items": items, "counts": {"open": open_count}}


def _urgency_key(item: dict[str, Any]) -> tuple[int, float]:
    created = item.get("created_at")
    stamp = datetime.fromisoformat(created) if created else None
    return urgency_sort_key(int(item["urgency"]), stamp)
