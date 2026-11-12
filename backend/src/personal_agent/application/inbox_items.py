"""JSON-friendly inbox items shared by the inbox API, Today and the approvals API.

Every item has a `kind` (`approval` | `suggestion`) so the UI picks a card from the kind, never
from the words in the text. Urgency is computed by the pure domain rule.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from personal_agent.domain.approvals import Approval, ApprovalStatus
from personal_agent.domain.suggestions import Suggestion, urgency_score


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def approval_payload(approval: Approval, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    return {
        "id": approval.id,
        "run_id": approval.run_id,
        "session_id": approval.session_id,
        "tool_name": approval.tool_name,
        "summary": approval.summary,
        "arguments": approval.arguments,
        "arguments_hash": approval.arguments_hash,
        "risk": approval.risk,
        "untrusted_content": approval.untrusted_content,
        "status": approval.status.value,
        "origin": approval.origin,
        "user_id": approval.user_id,
        "created_at": _iso(approval.created_at),
        "expires_at": _iso(approval.expires_at),
        "decided_at": _iso(approval.decided_at),
        "decided_by": approval.decided_by,
        "channel": approval.channel,
        "result": approval.result,
        "edited_from": approval.edited_from,
        "actionable": approval.status is ApprovalStatus.PENDING and not approval.is_expired(now),
    }


def suggestion_payload(suggestion: Suggestion, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    return {
        "id": suggestion.id,
        "kind": suggestion.kind,
        "title": suggestion.title,
        "reason": suggestion.reason,
        "source": suggestion.source,
        "status": suggestion.status,
        "proposed_action": suggestion.proposed_action,
        "expires_at": _iso(suggestion.expires_at),
        "created_at": _iso(suggestion.created_at),
        "decided_at": _iso(suggestion.decided_at),
        "feedback": suggestion.feedback,
        "outcome": suggestion.outcome,
        "approval_id": suggestion.approval_id,
        "actionable": suggestion.is_open and not suggestion.is_expired(now),
    }


def approval_item(approval: Approval, now: datetime) -> dict[str, Any]:
    payload = approval_payload(approval, now)
    return {
        "kind": "approval",
        "id": approval.id,
        "title": approval.summary,
        "summary": approval.summary,
        "status": payload["status"],
        "actionable": payload["actionable"],
        "urgency": urgency_score(
            "approval", risk=approval.risk, expires_at=approval.expires_at, now=now
        ),
        "run_id": approval.run_id,
        "tool_name": approval.tool_name,
        "risk": approval.risk,
        "untrusted_content": approval.untrusted_content,
        "created_at": payload["created_at"],
        "expires_at": payload["expires_at"],
        "decided_at": payload["decided_at"],
        "approval": payload,
    }


def suggestion_item(suggestion: Suggestion, now: datetime) -> dict[str, Any]:
    payload = suggestion_payload(suggestion, now)
    return {
        "kind": "suggestion",
        "id": suggestion.id,
        "title": suggestion.title,
        "summary": suggestion.title,
        "status": suggestion.status,
        "actionable": payload["actionable"],
        "urgency": urgency_score("suggestion", expires_at=suggestion.expires_at, now=now),
        "reason": suggestion.reason,
        "source": suggestion.source,
        "created_at": payload["created_at"],
        "expires_at": payload["expires_at"],
        "decided_at": payload["decided_at"],
        "suggestion": payload,
    }
