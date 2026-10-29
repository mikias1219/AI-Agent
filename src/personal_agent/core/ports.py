"""Contracts (Protocols) the core depends on, and only this.

Everything outside — Ollama, SQLite storage, memory, integrations — is an adapter
implementing one of these Protocols. Swapping adapters changes nothing in `core/`
or `services/`, which is the property that makes cloud providers, PostgreSQL,
and vector retrieval drop-in additions later.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from personal_agent.core.types import (
    ApprovalDecision,
    AssistantTurn,
    Message,
    Task,
    TaskStatus,
    ToolCall,
    ToolContext,
    ToolResult,
    ToolSpec,
)


@runtime_checkable
class ModelProvider(Protocol):
    """Provider-independent chat contract; adapters translate wire formats."""

    def chat(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> AssistantTurn:
        """Generate one assistant turn, optionally requesting tool calls."""
        ...


@runtime_checkable
class ToolRegistry(Protocol):
    """Contract shared between provider implementations (core side) and adapters."""

    def specs(self) -> list[ToolSpec]: ...

    def execute(self, call: ToolCall, ctx: ToolContext) -> ToolResult: ...


@runtime_checkable
class MemoryStore(Protocol):
    """Personal preferences, facts, and recall."""

    def remember(self, user_id: str, kind: str, content: str) -> None:
        """Persist a fact; duplicates are dropped by the adapter."""
        ...

    def recall(self, user_id: str, kind: str | None = None, limit: int = 10) -> list[str]:
        """Return most recent, most relevant facts (searchable adapters evolve here)."""
        ...


@runtime_checkable
class ConversationRepository(Protocol):
    """Persistence of conversation sessions and their messages."""

    def create_session(self, user_id: str) -> str: ...

    def append(self, session_id: str, message: Message) -> None: ...

    def load(self, session_id: str, limit: int = 50) -> list[Message]: ...


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
class ApprovalGateway(Protocol):
    """Human-in-the-loop gate for risky actions, decided by application code."""

    def request(self, call: ToolCall, ctx: ToolContext) -> ApprovalDecision:
        """Ask a human to approve; may be interactive ('cli') or async ('api')."""
        ...

    def decide(self, approval_id: str, approve: bool) -> None:
        """Record a human decision on a pending approval row."""
        ...


@runtime_checkable
class AuditLog(Protocol):
    """Tamper-evident trail of permission decisions, executions, and changes."""

    def record(self, event: str, actor: str, details: Mapping[str, Any]) -> None: ...


@runtime_checkable
class SettingsSource(Protocol):
    """Read settings from `.env` + process environment (adapter: pydantic-settings)."""

    def value(self, key: str, default: str | None = None) -> str | None: ...
