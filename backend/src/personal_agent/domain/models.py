"""Shared domain types across every layer.

These dataclasses are the *contract shapes* exchanged between the agent core, providers,
tools, and repositories. Adapters (Ollama HTTP, SQLAlchemy rows) convert to and from
these types so the domain never leaks into infrastructure.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]

AccessKind = Literal["read", "prepare", "execute"]

ApprovalDecision = Literal["approved", "denied", "deferred"]


@dataclass(slots=True)
class Message:
    """A single turn in a conversation, independent of any provider wire format."""

    role: Role
    content: str = ""
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    """Metadata for one persisted conversation."""

    id: str
    user_id: str
    created_at: datetime


@dataclass(slots=True)
class ToolCall:
    """A tool invocation requested by the model (or built by application code)."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """Outcome of a tool execution, shown back to the model verbatim."""

    tool_name: str
    ok: bool
    output: str = ""
    error: str | None = None


@dataclass(slots=True)
class ToolContext:
    """Who/where a tool call happened; passed by the interface layer, not the model."""

    user_id: str
    session_id: str
    origin: str  # Interface that initiated the action, e.g. cli, dashboard, or telegram.


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Declarative definition of one available tool (the provider-facing contract)."""

    name: str
    description: str
    parameters_schema: Mapping[str, Any]  # JSON Schema for arguments
    access_kind: AccessKind  # read | prepare | execute
    handler: Callable[[ToolContext, Mapping[str, Any]], str]


@dataclass(slots=True)
class AssistantTurn:
    """Provider-independent answer: final text and/or requested tool calls."""

    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(slots=True)
class RunOutcome:
    """The whole result of one `chat turn`, after tools ran."""

    final_text: str
    new_messages: list[Message] = field(default_factory=list)
    tool_calls_made: list[ToolCall] = field(default_factory=list)
    approvals_requested: list[str] = field(default_factory=list)


class TaskStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Task:
    """A tracked unit of work with lifecycle state."""

    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PLANNED
    owner_user_id: str = "default"
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceAccount:
    """Single local workspace owner; password hashes never belong in API payloads."""

    name: str
    email: str
    password_hash: str
