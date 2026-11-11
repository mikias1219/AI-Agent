"""Provider, storage, and execution contracts used by the application.

Everything outside — Ollama, SQLite storage, memory, integrations — is an adapter
implementing one of these Protocols. Swapping adapters changes nothing in `domain/`
or `application/services/`, which is the property that makes cloud providers, PostgreSQL,
and vector retrieval drop-in additions later.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from personal_agent.domain.approvals import Approval, ApprovalStatus
from personal_agent.domain.memory import Memory, MemoryKind
from personal_agent.domain.models import (
    AgentRun,
    ApprovalDecision,
    AssistantTurn,
    ConversationSummary,
    Message,
    OwnerProfile,
    RunEvent,
    RunStep,
    Task,
    TaskStatus,
    ToolCall,
    ToolContext,
    ToolResult,
    ToolSpec,
    WorkspaceAccount,
)


@runtime_checkable
class ModelProvider(Protocol):
    """Provider-independent chat contract; adapters translate wire formats."""

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        on_token: Callable[[str], None] | None = None,
    ) -> AssistantTurn:
        """Generate one assistant turn, optionally requesting tool calls."""
        ...


@runtime_checkable
class ToolRegistry(Protocol):
    """Contract shared between provider implementations (core side) and adapters."""

    def specs(self) -> list[ToolSpec]: ...

    def execute(self, call: ToolCall, ctx: ToolContext) -> ToolResult: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Text → vector; local hashing or hosted model behind one port (MEM-04)."""

    @property
    def dimensions(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...


@runtime_checkable
class MemoryStore(Protocol):
    """Owner-controlled memories with hybrid recall (MEM-01..04)."""

    def remember(
        self,
        user_id: str,
        kind: str,
        content: str,
        *,
        source_run_id: str | None = None,
    ) -> Memory | None:
        """Persist a memory; duplicates return the existing row; redaction raises."""
        ...

    def recall(
        self,
        user_id: str,
        kind: str | None = None,
        limit: int = 8,
        query: str | None = None,
    ) -> list[str]:
        """Hybrid top-N content strings for the system prompt."""
        ...

    def get(self, memory_id: str) -> Memory | None: ...

    def list(
        self,
        user_id: str,
        *,
        kind: MemoryKind | None = None,
        q: str | None = None,
        limit: int = 100,
    ) -> list[Memory]: ...

    def update(self, memory_id: str, *, content: str | None = None, kind: str | None = None) -> Memory: ...

    def soft_delete(self, memory_id: str) -> None: ...

    def forget_all(self, user_id: str) -> int: ...

    def search(self, user_id: str, query: str, *, limit: int = 8) -> list[Memory]: ...

    def mark_used(self, memory_ids: Sequence[str]) -> None: ...


@runtime_checkable
class ConversationRepository(Protocol):
    """Persistence of conversation sessions and their messages."""

    def create_session(self, user_id: str) -> str: ...

    def append(self, session_id: str, message: Message) -> None: ...

    def load(self, session_id: str, limit: int = 50) -> list[Message]: ...

    def latest_session(self, user_id: str) -> str | None: ...

    def list_sessions(self, limit: int = 50) -> list[ConversationSummary]: ...


@runtime_checkable
class TaskRepository(Protocol):
    """Persistence of domain tasks."""

    def add(self, task: Task) -> None: ...

    def get(self, task_id: str) -> Task | None: ...

    def list(self, status: TaskStatus | None = None) -> list[Task]: ...

    def save(self, task: Task) -> None:
        """Update an existing task (status, fields)."""
        ...


@runtime_checkable
class OwnerProfileRepository(Protocol):
    """Persistence of per-owner preferences (timezone, language)."""

    def get(self, owner_id: str) -> OwnerProfile | None: ...

    def save(self, profile: OwnerProfile) -> None: ...


@runtime_checkable
class ApprovalGateway(Protocol):
    """Human-in-the-loop gate for risky actions, decided by application code."""

    def request(
        self,
        call: ToolCall,
        ctx: ToolContext,
        *,
        access_kind: str = "execute",
        description: str = "",
    ) -> ApprovalDecision:
        """Ask a human to approve.

        Interactive interfaces (CLI) answer inline. Durable interfaces persist a pending
        approval and raise `ApprovalPendingError` so the run can pause (APR-02).
        """
        ...

    def claim(self, approval_id: str, call: ToolCall, ctx: ToolContext) -> None:
        """Consume an approved approval for exactly this call, once (BR-03).

        Raises `PermissionDeniedError` when it is unknown, not approved, expired, already
        used, or the tool or arguments differ from what was approved.
        """
        ...

    def finish(self, approval_id: str, *, ok: bool, result: str) -> None:
        """Record the outcome of an approved execution (executed or failed)."""
        ...


@runtime_checkable
class AuditLog(Protocol):
    """Operational trail of permission decisions, executions, and changes."""

    def record(self, event: str, actor: str, details: Mapping[str, Any]) -> None: ...


class AuditReader(Protocol):
    """Read-side view of the audit trail for operations/dashboard queries."""

    def list_recent(
        self, limit: int = 50, offset: int = 0, events: list[str] | None = None
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class SettingsSource(Protocol):
    """Read settings from `.env` + process environment (adapter: pydantic-settings)."""

    def value(self, key: str, default: str | None = None) -> str | None: ...


class WorkspaceAccountRepository(Protocol):
    """Storage contract for the single local workspace account."""

    def get(self) -> WorkspaceAccount | None: ...

    def create(self, account: WorkspaceAccount) -> None: ...

    def update_password(self, password_hash: str) -> None: ...


@runtime_checkable
class EventSink(Protocol):
    """Receives run events in order (AGT-02). Implementations must never raise into the agent."""

    def emit(self, event: RunEvent) -> None: ...


@runtime_checkable
class AgentRunRepository(Protocol):
    """Persistence of AgentRun and its steps."""

    def create(self, run: AgentRun) -> None: ...

    def get(self, run_id: str) -> AgentRun | None: ...

    def save(self, run: AgentRun) -> None: ...

    def list_recent(self, user_id: str | None = None, limit: int = 50) -> list[AgentRun]: ...

    def add_step(self, step: RunStep) -> None: ...

    def save_step(self, step: RunStep) -> None: ...

    def list_steps(self, run_id: str) -> list[RunStep]: ...


@runtime_checkable
class ApprovalStore(Protocol):
    """Persistence of approvals. `transition` is a compare-and-set, the idempotency anchor."""

    def create(self, approval: Approval) -> None: ...

    def get(self, approval_id: str) -> Approval | None: ...

    def find(
        self, status: ApprovalStatus | None = None, run_id: str | None = None, limit: int = 50
    ) -> list[Approval]: ...

    def list_expired(self, now: datetime) -> list[Approval]:
        """Pending approvals whose expiry has passed."""
        ...

    def transition(
        self,
        approval_id: str,
        from_statuses: Sequence[ApprovalStatus],
        to_status: ApprovalStatus,
        *,
        now: datetime,
        decided_by: str | None = None,
        channel: str | None = None,
        result: str | None = None,
    ) -> bool:
        """Atomically move to `to_status` only if currently in `from_statuses`."""
        ...
