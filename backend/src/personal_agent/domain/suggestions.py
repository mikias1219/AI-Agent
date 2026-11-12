"""Suggestions (spec §9.3) and inbox urgency ordering.

A suggestion is something AURA proposes unprompted. Every one MUST cite its source (what data
the idea came from) so the owner can judge it; a suggestion without a citation is rejected here.
Accepting never bypasses a gate: a proposed tool action still runs through the tool registry,
whose own approval rules (hard ceilings, BR-01..BR-14) apply. Nothing here imports
infrastructure, application or presentation code.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

SUGGESTION_STATUSES: frozenset[str] = frozenset({"new", "accepted", "dismissed", "expired"})
# What accepting actually did. `pending_approval` means a gate now waits for the owner.
SUGGESTION_OUTCOMES: frozenset[str] = frozenset({"", "acknowledged", "done", "pending_approval"})

MAX_TITLE = 256
MAX_TEXT = 1000
MAX_SOURCE = 256
MAX_KIND = 32
MAX_FEEDBACK = 500

# Urgency base scores. Approvals block a paused run or action, so they outrank ideas.
APPROVAL_URGENCY: Mapping[str, int] = {"high": 90, "medium": 70, "low": 50}
SUGGESTION_URGENCY = 30
EXPIRY_BONUS_WINDOW = timedelta(hours=24)
EXPIRY_BONUS_MAX = 9


class SuggestionError(ValueError):
    """A suggestion rule was violated (bad input or illegal state change)."""


@dataclass(slots=True)
class Suggestion:
    id: str
    owner_user_id: str
    kind: str
    title: str
    reason: str
    source: str  # required citation: where the idea came from
    status: str  # new | accepted | dismissed | expired
    proposed_action: dict[str, Any] = field(default_factory=dict)
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    decided_at: datetime | None = None
    feedback: str = ""  # why the owner dismissed it (kept so AURA can learn)
    outcome: str = ""  # what accepting did; see SUGGESTION_OUTCOMES
    approval_id: str | None = None  # the approval accepting created, if any

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at

    @property
    def is_open(self) -> bool:
        return self.status == "new"


# -- validation -----------------------------------------------------------------


def _clean(raw: str, *, what: str, limit: int, required: bool = True) -> str:
    text = (raw or "").strip()
    if required and not text:
        raise SuggestionError(f"{what} is required.")
    if len(text) > limit:
        raise SuggestionError(f"{what} must be at most {limit} characters.")
    return text


def clean_title(raw: str) -> str:
    return _clean(raw, what="Title", limit=MAX_TITLE)


def clean_reason(raw: str) -> str:
    return _clean(raw, what="Reason", limit=MAX_TEXT)


def clean_source(raw: str) -> str:
    """The citation is mandatory: never invent or default one."""
    return _clean(raw, what="Source citation", limit=MAX_SOURCE)


def clean_kind(raw: str) -> str:
    return _clean(raw, what="Kind", limit=MAX_KIND).lower()


def clean_feedback(raw: str | None) -> str:
    return _clean(raw or "", what="Feedback", limit=MAX_FEEDBACK, required=False)


def clean_proposed_action(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """`{}` (nothing to run) or `{"tool_name": str, "arguments": {...}}`."""
    if not raw:
        return {}
    extra = set(raw) - {"tool_name", "arguments"}
    if extra:
        raise SuggestionError(f"Unknown proposed_action fields: {', '.join(sorted(extra))}.")
    tool_name = str(raw.get("tool_name") or "").strip()
    if not tool_name:
        raise SuggestionError("proposed_action needs a tool_name.")
    arguments = raw.get("arguments") or {}
    if not isinstance(arguments, Mapping):
        raise SuggestionError("proposed_action arguments must be an object.")
    return {"tool_name": tool_name, "arguments": dict(arguments)}


# -- transitions ------------------------------------------------------------------


def expire_if_due(suggestion: Suggestion, now: datetime) -> bool:
    """Move an overdue open suggestion to `expired`. Returns whether it changed."""
    if suggestion.status == "new" and suggestion.is_expired(now):
        suggestion.status = "expired"
        suggestion.updated_at = now
        return True
    return False


def accept_suggestion(
    suggestion: Suggestion, *, now: datetime, outcome: str, approval_id: str | None = None
) -> None:
    if suggestion.status != "new":
        raise SuggestionError(f"Suggestion is already {suggestion.status}.")
    if outcome not in SUGGESTION_OUTCOMES or not outcome:
        raise SuggestionError(f"Unknown outcome '{outcome}'.")
    suggestion.status = "accepted"
    suggestion.outcome = outcome
    suggestion.approval_id = approval_id
    suggestion.decided_at = now
    suggestion.updated_at = now


def dismiss_suggestion(suggestion: Suggestion, *, now: datetime, feedback: str = "") -> None:
    if suggestion.status != "new":
        raise SuggestionError(f"Suggestion is already {suggestion.status}.")
    suggestion.status = "dismissed"
    suggestion.feedback = clean_feedback(feedback)
    suggestion.decided_at = now
    suggestion.updated_at = now


# -- urgency ----------------------------------------------------------------------


def urgency_score(
    kind: str, *, risk: str = "medium", expires_at: datetime | None, now: datetime
) -> int:
    """Higher means the owner should look sooner. Pure and deterministic.

    Approvals rank by risk, suggestions sit below all approvals; either gets up to +9 as its
    expiry gets close (within 24h), so a nearly-expired item never hides behind a calm one.
    """
    base = APPROVAL_URGENCY.get(risk, 70) if kind == "approval" else SUGGESTION_URGENCY
    if expires_at is None:
        return base
    remaining = expires_at - now
    if remaining >= EXPIRY_BONUS_WINDOW:
        return base
    fraction = 1.0 - max(remaining, timedelta(0)) / EXPIRY_BONUS_WINDOW
    return base + round(EXPIRY_BONUS_MAX * fraction)


_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def urgency_sort_key(urgency: int, created_at: datetime | None) -> tuple[int, float]:
    """Sort ascending to get most urgent first, newest first within equal urgency."""
    stamp = (created_at or _EPOCH).timestamp()
    return (-urgency, -stamp)
