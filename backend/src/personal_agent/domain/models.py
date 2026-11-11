"""Shared domain types across every layer.

These dataclasses are the *contract shapes* exchanged between the agent core, providers,
tools, and repositories. Adapters (Ollama HTTP, SQLAlchemy rows) convert to and from
these types so the domain never leaks into infrastructure.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from personal_agent.domain.ports import EventSink

Role = Literal["system", "user", "assistant", "tool"]

AccessKind = Literal["read", "prepare", "execute", "destructive"]

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
    run_id: str | None = None  # AgentRun this call belongs to, when one exists.
    events: EventSink | None = None  # Lets gates (approvals) report onto the run's stream.


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Declarative definition of one available tool (the provider-facing contract)."""

    name: str
    description: str
    parameters_schema: Mapping[str, Any]  # JSON Schema for arguments
    access_kind: AccessKind  # read | prepare | execute | destructive
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
    stop_reason: str | None = None  # None | "cancelled" | "limit_rounds" | "limit_time"


class TaskStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    NONE = "none"


@dataclass(slots=True)
class Task:
    """A tracked unit of work with lifecycle state.

    `description` holds the free-text notes (the API exposes it as `notes`). `deleted_at`
    marks a soft delete: such tasks stay in storage but are hidden from default lists.
    """

    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PLANNED
    owner_user_id: str = "default"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    priority: TaskPriority = TaskPriority.NONE
    due_at: datetime | None = None  # timezone-aware when set
    project: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    source_ref: str = ""
    completed_at: datetime | None = None
    deleted_at: datetime | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


@dataclass(slots=True)
class OwnerProfile:
    """Per-owner preferences used to resolve dates and language."""

    owner_id: str
    name: str | None = None
    timezone: str = "UTC"
    language: str = "en"


@dataclass(frozen=True, slots=True)
class WorkspaceAccount:
    """Single local workspace owner; password hashes never belong in API payloads."""

    name: str
    email: str
    password_hash: str


class RunStatus(StrEnum):
    """Lifecycle of an AgentRun (AGT-01). `awaiting_approval` is reserved for P3."""

    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED)


class StepStatus(StrEnum):
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"


@dataclass(slots=True)
class AgentRun:
    """One persisted agent turn: who asked, which prompt version answered, how it ended."""

    id: str
    session_id: str
    user_id: str
    origin: str
    prompt_version: str
    status: RunStatus = RunStatus.RUNNING
    input_text: str = ""
    final_text: str = ""
    error: str = ""
    stop_reason: str | None = None
    model: str = ""
    created_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(slots=True)
class RunStep:
    """One tool step of a run, persisted with timings (AGT-02, OBS-01)."""

    id: str
    run_id: str
    seq: int
    kind: str  # "tool"
    name: str
    status: StepStatus = StepStatus.RUNNING
    arguments: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    error: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None


RUN_EVENT_TYPES = (
    "run.started",
    "token",
    "tool.started",
    "tool.finished",
    "approval.required",
    "approval.resolved",
    "run.completed",
    "run.failed",
)


@dataclass(frozen=True, slots=True)
class RunEvent:
    """An event on a run's stream; `seq` is assigned by the sink, starting at 1."""

    run_id: str
    type: str
    data: Mapping[str, Any] = field(default_factory=dict)
    seq: int = 0


class CancellationToken:
    """Cooperative cancel flag checked by the agent between steps."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()
