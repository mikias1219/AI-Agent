"""Owner-facing memory use cases (MEM-02, MEM-03, MEM-08)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from personal_agent.application.onboarding_marker import OnboardingMarker
from personal_agent.domain.exceptions import AgentError, StorageError
from personal_agent.domain.memory import MEMORY_KINDS, Memory, MemoryKind
from personal_agent.domain.ports import AuditLog, MemoryStore

FORGET_CONFIRM_PHRASE = "FORGET EVERYTHING"
_TOKEN_TTL = timedelta(minutes=15)
logger = logging.getLogger(__name__)


class MemoryService:
    """CRUD + propose/confirm + forget-all confirmation tokens."""

    def __init__(
        self,
        store: MemoryStore,
        *,
        audit: AuditLog | None = None,
        secret: str = "memory-forget",
        onboarding: OnboardingMarker | None = None,
    ) -> None:
        self._store = store
        self._audit = audit
        self._secret = secret.encode("utf-8")
        self._tokens: dict[str, datetime] = {}
        self._onboarding = onboarding

    def propose(
        self,
        user_id: str,
        kind: str,
        content: str,
        *,
        source_run_id: str | None = None,
        source: str = "",
    ) -> dict[str, str]:
        """Validate and persist a pending proposal without writing memory (MEM-02)."""
        return self._store.create_proposal(
            user_id,
            kind,
            content,
            source_run_id=source_run_id,
            source=source,
        )

    def list_proposals(self, user_id: str) -> Sequence[dict[str, str]]:
        return self._store.list_proposals(user_id)

    def confirm_proposal(self, user_id: str, proposal_id: str) -> Memory:
        proposal = self._store.get_proposal(proposal_id)
        if proposal is None or proposal.get("user_id") != user_id:
            raise StorageError(f"Unknown memory proposal '{proposal_id}'.")
        if proposal.get("status") != "proposed":
            raise AgentError(f"Proposal is already {proposal.get('status')}.")
        memory = self.create(
            user_id,
            proposal["kind"],
            proposal["content"],
            source_run_id=proposal.get("source_run_id") or None,
            actor=user_id,
        )
        self._store.mark_proposal(proposal_id, status="saved")
        return memory

    def dismiss_proposal(self, user_id: str, proposal_id: str) -> None:
        proposal = self._store.get_proposal(proposal_id)
        if proposal is None or proposal.get("user_id") != user_id:
            raise StorageError(f"Unknown memory proposal '{proposal_id}'.")
        if proposal.get("status") != "proposed":
            raise AgentError(f"Proposal is already {proposal.get('status')}.")
        self._store.mark_proposal(proposal_id, status="dismissed")
        self._record("memory.proposal_dismissed", user_id, {"id": proposal_id})

    def create(
        self,
        user_id: str,
        kind: str,
        content: str,
        *,
        source_run_id: str | None = None,
        actor: str | None = None,
    ) -> Memory:
        memory = self._store.remember(user_id, kind, content, source_run_id=source_run_id)
        if memory is None:
            raise AgentError("Memory could not be saved.")
        self._record(
            "memory.created",
            actor or user_id,
            {"id": memory.id, "kind": memory.kind},
        )
        if self._onboarding is not None:
            try:
                self._onboarding.mark(user_id, "saved_memory")
            except Exception:  # noqa: BLE001
                logger.exception("Could not mark saved_memory checklist item")
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self._store.get(memory_id)

    def list(
        self,
        user_id: str,
        *,
        kind: MemoryKind | None = None,
        q: str | None = None,
        limit: int = 100,
    ) -> Sequence[Memory]:
        return self._store.list(user_id, kind=kind, q=q, limit=limit)

    def update(self, memory_id: str, user_id: str, **fields: str) -> Memory:
        current = self._require_owned(memory_id, user_id)
        content = fields.get("content")
        kind = fields.get("kind")
        updated = self._store.update(
            current.id,
            content=content,
            kind=kind,
        )
        self._record("memory.updated", user_id, {"id": updated.id})
        return updated

    def delete(self, memory_id: str, user_id: str) -> None:
        self._require_owned(memory_id, user_id)
        self._store.soft_delete(memory_id)
        self._record("memory.deleted", user_id, {"id": memory_id})

    def search(self, user_id: str, query: str, *, limit: int = 8) -> Sequence[Memory]:
        found = self._store.search(user_id, query, limit=limit)
        if found:
            self._store.mark_used([m.id for m in found])
        return found

    def issue_forget_token(self, user_id: str) -> dict[str, str]:
        """Issue a short-lived token; owner must type FORGET EVERYTHING to redeem."""
        nonce = secrets.token_urlsafe(16)
        digest = hmac.new(self._secret, f"{user_id}:{nonce}".encode(), hashlib.sha256).hexdigest()
        token = f"{nonce}.{digest}"
        self._tokens[token] = datetime.now(UTC) + _TOKEN_TTL
        return {
            "token": token,
            "confirm_phrase": FORGET_CONFIRM_PHRASE,
            "expires_in_seconds": str(int(_TOKEN_TTL.total_seconds())),
        }

    def forget_all(self, user_id: str, *, token: str, confirm_phrase: str) -> int:
        if confirm_phrase.strip() != FORGET_CONFIRM_PHRASE:
            raise AgentError(f'Type "{FORGET_CONFIRM_PHRASE}" to confirm.')
        expires = self._tokens.pop(token, None)
        if expires is None or expires < datetime.now(UTC):
            raise AgentError("Forget token is missing or expired. Request a new one.")
        nonce, _, digest = token.partition(".")
        expected = hmac.new(self._secret, f"{user_id}:{nonce}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, expected):
            raise AgentError("Forget token is invalid.")
        count = self._store.forget_all(user_id)
        self._record("memory.forget_all", user_id, {"count": count})
        return count

    def _require_owned(self, memory_id: str, user_id: str) -> Memory:
        memory = self._store.get(memory_id)
        if memory is None or memory.user_id != user_id:
            raise StorageError(f"Unknown memory '{memory_id}'.")
        return memory

    def _record(self, event: str, actor: str, details: dict[str, object]) -> None:
        if self._audit is not None:
            self._audit.record(event, actor, details)


__all__ = ["FORGET_CONFIRM_PHRASE", "MEMORY_KINDS", "MemoryService"]
