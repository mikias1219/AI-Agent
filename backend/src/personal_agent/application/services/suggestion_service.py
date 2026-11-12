"""Suggestions: create, list, accept, dismiss (spec §9.3). Owner-scoped and audited.

Accepting a suggestion that proposes a tool action hands that action to an injected executor,
which is wired to `ToolRegistry.execute`. The registry's approval gate therefore still applies:
an execute/destructive tool leaves the suggestion `accepted` with outcome `pending_approval`
and an approval waiting for the owner, never a claim that the action happened.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.ports import AuditLog, SuggestionRepository
from personal_agent.domain.suggestions import (
    Suggestion,
    SuggestionError,
    accept_suggestion,
    clean_kind,
    clean_proposed_action,
    clean_reason,
    clean_source,
    clean_title,
    dismiss_suggestion,
    expire_if_due,
)

OPEN_STATUSES: tuple[str, ...] = ("new",)
DONE_STATUSES: tuple[str, ...] = ("accepted", "dismissed", "expired")


@dataclass(frozen=True, slots=True)
class ActionOutcome:
    """What the tool registry did with an accepted suggestion's action."""

    state: str  # done | pending_approval | failed
    summary: str = ""
    approval_id: str | None = None


ActionExecutor = Callable[[str, str, dict[str, Any]], ActionOutcome]
AccessKindOf = Callable[[str], str | None]


class SuggestionActionFailedError(SuggestionError):
    """The proposed action could not run; the suggestion stays open so the owner can retry."""


@dataclass(frozen=True, slots=True)
class AcceptResult:
    suggestion: Suggestion
    outcome: str
    summary: str


class SuggestionService:
    def __init__(
        self,
        repository: SuggestionRepository,
        *,
        execute_action: ActionExecutor | None = None,
        access_kind_of: AccessKindOf | None = None,
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._execute = execute_action
        self._access_kind_of = access_kind_of
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    def create(
        self,
        owner_user_id: str,
        *,
        kind: str,
        title: str,
        reason: str,
        source: str,
        proposed_action: Mapping[str, Any] | None = None,
        expires_in: timedelta | None = None,
        origin: str = "agent",
    ) -> Suggestion:
        action = clean_proposed_action(proposed_action)
        tool_name = action.get("tool_name")
        if tool_name and self._access_kind_of is not None and not self._access_kind_of(tool_name):
            raise SuggestionError(f"proposed_action names unknown tool '{tool_name}'.")
        now = self._clock()
        suggestion = Suggestion(
            id=uuid.uuid4().hex,
            owner_user_id=owner_user_id,
            kind=clean_kind(kind),
            title=clean_title(title),
            reason=clean_reason(reason),
            source=clean_source(source),
            status="new",
            proposed_action=action,
            expires_at=now + expires_in if expires_in is not None else None,
            created_at=now,
            updated_at=now,
        )
        self._repository.add(suggestion)
        self._record("suggestion.created", suggestion, origin=origin, source=suggestion.source)
        return suggestion

    def get(self, suggestion_id: str, owner_user_id: str) -> Suggestion:
        suggestion = self._repository.get(suggestion_id)
        if suggestion is None or suggestion.owner_user_id != owner_user_id:
            raise StorageError(f"Unknown suggestion '{suggestion_id}'.")
        self._expire(suggestion)
        return suggestion

    def list(self, owner_user_id: str, status: str | None = None) -> Sequence[Suggestion]:
        self.expire_due(owner_user_id)
        statuses = None if status is None else (status,)
        return self._repository.list(owner_user_id, statuses)

    def open(self, owner_user_id: str) -> Sequence[Suggestion]:
        self.expire_due(owner_user_id)
        return self._repository.list(owner_user_id, OPEN_STATUSES)

    def done(self, owner_user_id: str, limit: int = 100) -> Sequence[Suggestion]:
        self.expire_due(owner_user_id)
        return self._repository.list(owner_user_id, DONE_STATUSES, limit)

    def expire_due(self, owner_user_id: str) -> int:
        count = 0
        for suggestion in self._repository.list(owner_user_id, OPEN_STATUSES):
            if self._expire(suggestion):
                count += 1
        return count

    def accept(self, suggestion_id: str, owner_user_id: str) -> AcceptResult:
        suggestion = self.get(suggestion_id, owner_user_id)
        now = self._clock()
        if suggestion.status != "new":
            raise SuggestionError(f"Suggestion is already {suggestion.status}.")
        tool_name = suggestion.proposed_action.get("tool_name")
        outcome, summary, approval_id = "acknowledged", "Noted. Nothing to run.", None
        if tool_name:
            if self._execute is None:
                raise SuggestionActionFailedError("Actions are not available right now.")
            result = self._execute(
                suggestion.owner_user_id,
                str(tool_name),
                dict(suggestion.proposed_action.get("arguments") or {}),
            )
            if result.state == "failed":
                self._record("suggestion.action_failed", suggestion, tool=tool_name)
                raise SuggestionActionFailedError(result.summary or "The action did not run.")
            outcome, summary, approval_id = result.state, result.summary, result.approval_id
        accept_suggestion(suggestion, now=now, outcome=outcome, approval_id=approval_id)
        self._repository.save(suggestion)
        self._record("suggestion.accepted", suggestion, outcome=outcome, approval_id=approval_id)
        return AcceptResult(suggestion, outcome, summary)

    def dismiss(self, suggestion_id: str, owner_user_id: str, feedback: str = "") -> Suggestion:
        suggestion = self.get(suggestion_id, owner_user_id)
        dismiss_suggestion(suggestion, now=self._clock(), feedback=feedback)
        self._repository.save(suggestion)
        self._record("suggestion.dismissed", suggestion, has_feedback=bool(suggestion.feedback))
        return suggestion

    # -- internals ------------------------------------------------------------

    def _expire(self, suggestion: Suggestion) -> bool:
        if expire_if_due(suggestion, self._clock()):
            self._repository.save(suggestion)
            self._record("suggestion.expired", suggestion)
            return True
        return False

    def _record(self, event: str, suggestion: Suggestion, **details: object) -> None:
        if self._audit is not None:
            self._audit.record(
                event,
                suggestion.owner_user_id,
                {"suggestion_id": suggestion.id, "kind": suggestion.kind, **details},
            )
