"""Approval records and pure rules (APR-01..06, BR-03..05).

An approval is the durable record of "the agent wants to run this tool with these exact
arguments". The arguments hash binds the owner's decision to one payload: editing the
arguments creates a new approval with a new hash and supersedes the old one (APR-06).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

DEFAULT_APPROVAL_TTL = timedelta(hours=24)  # APR-05

# Channels allowed to decide (APR-04): the authenticated dashboard and the owner's private
# Telegram chat. Group chats and non-allowlisted users never decide.
DECIDING_CHANNELS = frozenset({"dashboard", "telegram_private"})


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"
    SUPERSEDED = "superseded"  # replaced by an edited approval (new hash)

    @property
    def is_final(self) -> bool:
        return self is not ApprovalStatus.PENDING and self is not ApprovalStatus.APPROVED


@dataclass(slots=True)
class Approval:
    """One persisted approval request."""

    id: str
    tool_name: str
    arguments: dict[str, Any]
    arguments_hash: str
    user_id: str = "default"
    session_id: str = ""
    origin: str = "cli"
    run_id: str | None = None
    call_id: str = ""  # tool call id in the transcript this approval answers
    risk: str = "medium"  # low | medium | high
    summary: str = ""
    untrusted_content: bool = False  # BR-04: external content influenced this run
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime | None = None
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    decided_by: str = ""
    channel: str = ""
    result: str = ""
    edited_from: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at


def arguments_hash(arguments: Mapping[str, Any]) -> str:
    """Stable SHA-256 over canonical JSON, so equal payloads hash equally."""
    canonical = json.dumps(
        dict(arguments), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def risk_level(access_kind: str, tool_name: str = "") -> str:
    """Plain risk label for the approval card."""
    if access_kind == "destructive" or "send" in tool_name or "email" in tool_name:
        return "high"
    if access_kind == "execute":
        return "medium"
    return "low"


def summarize_call(tool_name: str, description: str = "") -> str:
    """One plain-language line describing what will happen."""
    first = description.strip().split(". ")[0].strip().rstrip(".")
    if first:
        return first[:160]
    return tool_name.replace("_", " ").capitalize()


def declined_message(status: ApprovalStatus, summary: str) -> str:
    """What AURA tells the owner when an action was not run."""
    what = summary or "that action"
    if status is ApprovalStatus.EXPIRED:
        return (
            f"The approval request expired, so I did not run it: {what}. "
            "Ask me again if you still want it."
        )
    return f"Understood. You denied it, so I did not run it: {what}."
