"""SQLAlchemy ORM models — the database schema.

Deliberately separate from `domain/models.py`: the domain never becomes an ORM class
and the schema can evolve (Alembic) without touching business logic. Mapping to/from
domain types lives in `repositories.py`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Column default: timezone-naive is avoided; store UTC."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for every ORM model in the project."""


class MessageRow(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    name: Mapped[str | None] = mapped_column(String(64))
    tool_call_id: Mapped[str | None] = mapped_column(String(64))
    tool_calls_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConversationRow(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True, default="default")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="planned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    priority: Mapped[str] = mapped_column(String(8), default="none", server_default="none")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    project: Mapped[str] = mapped_column(String(128), default="", server_default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(64), default="", server_default="")
    source_ref: Mapped[str] = mapped_column(String(256), default="", server_default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    plan_date: Mapped[date | None] = mapped_column(Date, index=True)
    recurrence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    blocked_by: Mapped[list | None] = mapped_column(JSON, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float)
    target_unit: Mapped[str] = mapped_column(String(20), default="", server_default="")
    actual_value: Mapped[float | None] = mapped_column(Float)
    outcome: Mapped[str | None] = mapped_column(String(16))
    outcome_note: Mapped[str] = mapped_column(String(500), default="", server_default="")
    calendar_event_id: Mapped[str | None] = mapped_column(String(128))
    calendar_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OwnerProfileRow(Base):
    __tablename__ = "owner_profile"

    owner_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(80))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    language: Mapped[str] = mapped_column(String(16), default="en", server_default="en")
    wizard_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    checklist: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    agent_control_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str] = mapped_column(String(500), default="", server_default="")
    birthday: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notification_prefs: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MemoryRow(Base):
    """Owner-controlled memory (MEM-01). Soft-deleted rows keep content until forget-all."""

    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True, default="fact")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_run_id: Mapped[str | None] = mapped_column(String(64))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "kind", "content", name="uq_memories_user_kind_content"),
    )


class MemoryProposalRow(Base):
    """Pending memory write waiting for owner Save/Dismiss (MEM-02, Memory Proposed tab)."""

    __tablename__ = "memory_proposals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True, default="fact")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_run_id: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(String(16), index=True, default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalRow(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # provided by gateway
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, default="{}")
    user_id: Mapped[str] = mapped_column(String(128), index=True, default="default")
    session_id: Mapped[str] = mapped_column(String(64), default="")
    origin: Mapped[str] = mapped_column(String(32), default="cli")
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # P3 (APR-01): durable approvals
    run_id: Mapped[str | None] = mapped_column(String(64), index=True)
    call_id: Mapped[str] = mapped_column(String(64), default="", server_default="")
    arguments_hash: Mapped[str] = mapped_column(String(64), default="", server_default="")
    risk: Mapped[str] = mapped_column(String(16), default="medium", server_default="medium")
    summary: Mapped[str] = mapped_column(Text, default="")
    untrusted_content: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    decided_by: Mapped[str] = mapped_column(String(128), default="", server_default="")
    channel: Mapped[str] = mapped_column(String(32), default="", server_default="")
    result: Mapped[str] = mapped_column(Text, default="")
    edited_from: Mapped[str | None] = mapped_column(String(64))


class AuditEntryRow(Base):
    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    actor: Mapped[str] = mapped_column(String(128), default="agent")
    event: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    details_json: Mapped[str] = mapped_column(JSON, default=dict)


class WorkspaceAccountRow(Base):
    __tablename__ = "workspace_accounts"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GoogleConnectionRow(Base):
    """Local Google OAuth connection metadata (tokens never returned to the browser)."""

    __tablename__ = "google_connections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    email: Mapped[str] = mapped_column(String(254), default="")
    connected: Mapped[int] = mapped_column(Integer, default=0)  # 0/1 for SQLite simplicity
    access_token: Mapped[str] = mapped_column(Text, default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    scopes: Mapped[str] = mapped_column(Text, default="")
    read_only: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentRunRow(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    origin: Mapped[str] = mapped_column(String(32), default="cli")
    status: Mapped[str] = mapped_column(String(24), index=True, default="running")
    prompt_version: Mapped[str] = mapped_column(String(128), default="")
    model: Mapped[str] = mapped_column(String(128), default="", server_default="")
    trace_id: Mapped[str] = mapped_column(String(64), default="", server_default="")
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    input_text: Mapped[str] = mapped_column(Text, default="")
    final_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    stop_reason: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunStepRow(Base):
    __tablename__ = "run_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="tool")
    name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="running")
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    result_type: Mapped[str] = mapped_column(
        String(64), default="generic", server_default="generic"
    )
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class JobRow(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str] = mapped_column(Text, default="")
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReminderRow(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    task_id: Mapped[str | None] = mapped_column(String(64))
    channels: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    late: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AutomationRow(Base):
    __tablename__ = "automations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    schedule_time: Mapped[str] = mapped_column(String(8), default="08:00", server_default="08:00")
    channels: Mapped[list[str]] = mapped_column(JSON, default=list)
    quiet_hours_start: Mapped[str] = mapped_column(String(8), default="", server_default="")
    quiet_hours_end: Mapped[str] = mapped_column(String(8), default="", server_default="")
    daily_cap: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_result: Mapped[str] = mapped_column(Text, default="")
    last_run_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("owner_user_id", "kind", name="uq_automations_owner_kind"),)


class McpServerRow(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    transport: Mapped[str] = mapped_column(String(16), nullable=False, default="stdio")
    command: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    read_only: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tool_allowlist: Mapped[list[str]] = mapped_column(JSON, default=list)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=15.0, server_default="15")
    max_output_bytes: Mapped[int] = mapped_column(Integer, default=32768, server_default="32768")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GoalRow(Base):
    """A longer outcome the owner wants to reach (spec §9.2)."""

    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    success_criteria: Mapped[list[str]] = mapped_column(JSON, default=list)
    progress: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    status: Mapped[str] = mapped_column(String(16), index=True, default="active")
    next_step: Mapped[str] = mapped_column(Text, default="", server_default="")
    kind: Mapped[str] = mapped_column(String(16), default="goal", server_default="goal")
    target_hours: Mapped[float | None] = mapped_column(Float)
    milestones: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlanRow(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    goal_id: Mapped[str | None] = mapped_column(String(64), index=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(256), default="", server_default="")
    status: Mapped[str] = mapped_column(String(16), index=True, default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlanStepRow(Base):
    __tablename__ = "plan_steps"

    # Step ids ("s1", "s2"...) are local to a plan, so the key is (plan_id, id).
    plan_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("plans.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(128))
    access_kind: Mapped[str] = mapped_column(String(16), default="prepare")
    status: Mapped[str] = mapped_column(String(16), default="planned")
    depends_on: Mapped[list[str]] = mapped_column(JSON, default=list)
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[str] = mapped_column(Text, default="", server_default="")
    approval_id: Mapped[str | None] = mapped_column(String(64))


class SuggestionRow(Base):
    """Something Compass proposes unprompted; always carries a source citation (spec §9.3)."""

    __tablename__ = "suggestions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="idea")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    source: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, default="new")
    proposed_action: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    feedback: Mapped[str] = mapped_column(Text, default="", server_default="")
    outcome: Mapped[str] = mapped_column(String(24), default="", server_default="")
    approval_id: Mapped[str | None] = mapped_column(String(64))


class UndoActionRow(Base):
    """Reversible auto-run under Balanced (AG-TRU-04); open for 10 minutes."""

    __tablename__ = "undo_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    entity_id: Mapped[str] = mapped_column(String(128), default="", server_default="")
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), index=True, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NoteRow(Base):
    """Notes and diary entries. One diary entry per (owner, entry_date)."""

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(8), index=True)
    title: Mapped[str] = mapped_column(String(200), default="", server_default="")
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    mood: Mapped[str | None] = mapped_column(String(8))
    entry_date: Mapped[date | None] = mapped_column(Date)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("owner_user_id", "kind", "entry_date", name="uq_notes_owner_kind_date"),
    )


class FileRow(Base):
    """Library files; content is a BLOB in the database (ADR 0034)."""

    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(8), index=True)
    description: Mapped[str] = mapped_column(String(500), default="", server_default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProfilePhotoRow(Base):
    """Owner profile photo, kept apart from the Library files."""

    __tablename__ = "profile_photos"

    owner_user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    mime: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    etag: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LearnItemRow(Base):
    __tablename__ = "learn_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(8), default="word")
    term: Mapped[str] = mapped_column(String(200), nullable=False)
    term_key: Mapped[str] = mapped_column(String(200), nullable=False)  # casefolded term
    meaning: Mapped[str] = mapped_column(String(1000), default="")
    example: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    language: Mapped[str] = mapped_column(String(16), default="en", server_default="en")
    topic: Mapped[str] = mapped_column(String(60), default="", server_default="")
    box: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    times_correct: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    times_wrong: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("owner_user_id", "language", "term_key", name="uq_learn_owner_term"),
    )


class LearnReviewRow(Base):
    """One row per review; feeds the learning streak. Survives deleting the item."""

    __tablename__ = "learn_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    item_id: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(8))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReadingPlanRow(Base):
    __tablename__ = "reading_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    items: Mapped[list[str]] = mapped_column(JSON, default=list)
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReadingLogRow(Base):
    __tablename__ = "reading_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    read_on: Mapped[date] = mapped_column(Date, index=True)
    reflection: Mapped[str] = mapped_column(Text, default="", server_default="")
    plan_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DriveLinkRow(Base):
    """One Compass object mirrored to one Drive file (contract section 8)."""

    __tablename__ = "drive_links"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "object_type", "object_id", name="uq_drive_links_object"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    object_type: Mapped[str] = mapped_column(String(16))
    object_id: Mapped[str] = mapped_column(String(64))
    drive_file_id: Mapped[str] = mapped_column(String(200))
    drive_url: Mapped[str] = mapped_column(String(500), default="", server_default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="", server_default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Set when the Compass object was deleted locally. The Drive file is left untouched.
    local_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DriveFolderRow(Base):
    """Cached Drive folder ids by Compass-relative path, so folders are looked up once."""

    __tablename__ = "drive_folders"

    owner_user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    path: Mapped[str] = mapped_column(String(400), primary_key=True)
    folder_id: Mapped[str] = mapped_column(String(200))
    folder_url: Mapped[str] = mapped_column(String(500), default="", server_default="")


class SyncSettingsRow(Base):
    """Owner settings and last result for one sync service (`drive` or `calendar`)."""

    __tablename__ = "sync_settings"

    owner_user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    service: Mapped[str] = mapped_column(String(16), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    include: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str] = mapped_column(String(500), default="", server_default="")


# -- Sessions (S1): revocable server-side sessions -------------------------------------------


class UserSessionRow(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# -- Habits (P1-2) ---------------------------------------------------------------------------


class HabitRow(Base):
    __tablename__ = "habits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="habit", server_default="habit")
    rule: Mapped[dict] = mapped_column(JSON, default=dict)
    target_value: Mapped[float | None] = mapped_column(Float)
    target_unit: Mapped[str] = mapped_column(String(20), default="", server_default="")
    icon: Mapped[str] = mapped_column(String(16), default="", server_default="")
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    counts_toward_score: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HabitCheckinRow(Base):
    __tablename__ = "habit_checkins"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    habit_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(8), default="done")
    value: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str] = mapped_column(String(300), default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("habit_id", "day", name="uq_habit_checkin_day"),
        CheckConstraint("status in ('done','skipped')", name="ck_habit_checkin_status"),
    )


# -- Finance (section 6) ---------------------------------------------------------------------


class FinAccountRow(Base):
    __tablename__ = "fin_accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[str] = mapped_column(String(16), default="cash")
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    opening_balance_minor: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_fin_account_name"),
        CheckConstraint(
            "type in ('cash','bank','mobile_money','card')", name="ck_fin_account_type"
        ),
    )


class FinCategoryRow(Base):
    __tablename__ = "fin_categories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("fin_categories.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(8))
    icon: Mapped[str] = mapped_column(String(16), default="", server_default="")
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    __table_args__ = (
        UniqueConstraint("owner_user_id", "kind", "name", name="uq_fin_category_name"),
        CheckConstraint("kind in ('income','expense')", name="ck_fin_category_kind"),
    )


class FinTransactionRow(Base):
    __tablename__ = "fin_transactions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    account_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("fin_accounts.id", ondelete="RESTRICT")
    )
    category_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("fin_categories.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(10))
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(10), default="paid")
    merchant: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(String(500), default="", server_default="")
    budget_id: Mapped[str | None] = mapped_column(String(64))
    project_id: Mapped[str | None] = mapped_column(String(64))
    occurrence_id: Mapped[str | None] = mapped_column(String(64), index=True)
    transfer_group: Mapped[str | None] = mapped_column(String(64), index=True)
    receipt_file_id: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(8), default="user")
    approval_id: Mapped[str | None] = mapped_column(String(64))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_fin_tx_amount_positive"),
        CheckConstraint("kind in ('income','expense','transfer')", name="ck_fin_tx_kind"),
        Index("ix_fin_tx_owner_when", "owner_user_id", "occurred_at"),
        CheckConstraint("status in ('received','paid','partial')", name="ck_fin_tx_status"),
    )


class FinRecurringRuleRow(Base):
    __tablename__ = "fin_recurring_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    group_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(120))
    amount_minor: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("fin_categories.id", ondelete="SET NULL")
    )
    account_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("fin_accounts.id", ondelete="SET NULL")
    )
    rule: Mapped[dict] = mapped_column(JSON, default=dict)
    remind_days_before: Mapped[int] = mapped_column(Integer, default=3)
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)

    __table_args__ = (
        CheckConstraint("kind in ('income','bill')", name="ck_fin_rule_kind"),
        CheckConstraint("amount_minor > 0", name="ck_fin_rule_amount_positive"),
    )


class FinOccurrenceRow(Base):
    __tablename__ = "fin_occurrences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    rule_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("fin_recurring_rules.id", ondelete="CASCADE"), index=True
    )
    rule_version: Mapped[int] = mapped_column(Integer, default=1)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    expected_minor: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="expected")
    paid_minor: Mapped[int] = mapped_column(Integer, default=0)
    transaction_id: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint("rule_id", "due_date", name="uq_fin_occurrence_rule_due"),
        CheckConstraint(
            "status in ('expected','paid','partial','overdue','skipped')",
            name="ck_fin_occurrence_status",
        ),
    )


class FinBudgetRow(Base):
    __tablename__ = "fin_budgets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(10), default="monthly")
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    income_plan_minor: Mapped[int] = mapped_column(Integer, default=0)
    rollover: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    __table_args__ = (
        CheckConstraint(
            "type in ('monthly','weekly','category','project','savings','emergency','special')",
            name="ck_fin_budget_type",
        ),
    )


class FinBudgetLineRow(Base):
    __tablename__ = "fin_budget_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    budget_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("fin_budgets.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("fin_categories.id", ondelete="CASCADE")
    )
    planned_minor: Mapped[int] = mapped_column(Integer)
    alert_at_pct: Mapped[int] = mapped_column(Integer, default=80)

    __table_args__ = (UniqueConstraint("budget_id", "category_id", name="uq_fin_budget_line"),)


class FinSavingsGoalRow(Base):
    __tablename__ = "fin_savings_goals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(120))
    goal_id: Mapped[str | None] = mapped_column(String(64))
    target_minor: Mapped[int] = mapped_column(Integer)
    target_date: Mapped[date | None] = mapped_column(Date)
    monthly_contribution_minor: Mapped[int] = mapped_column(Integer, default=0)
    account_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("fin_accounts.id", ondelete="SET NULL")
    )
    currency: Mapped[str] = mapped_column(String(3), default="ETB")


class FinContributionRow(Base):
    __tablename__ = "fin_contributions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    savings_goal_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("fin_savings_goals.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[str | None] = mapped_column(String(64))
    amount_minor: Mapped[int] = mapped_column(Integer)
    contributed_on: Mapped[date] = mapped_column(Date)


# -- Time tracking (P2-2) --------------------------------------------------------------------


class TimeEntryRow(Base):
    __tablename__ = "time_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    task_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    goal_id: Mapped[str | None] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(128), default="", server_default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(300), default="", server_default="")
    source: Mapped[str] = mapped_column(String(8), default="timer", server_default="timer")

    __table_args__ = (
        CheckConstraint("ended_at is null or ended_at >= started_at", name="ck_time_order"),
        CheckConstraint("source in ('timer','manual')", name="ck_time_source"),
    )


# -- Projects (P2-1) -------------------------------------------------------------------------


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="active")
    deadline: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_project_owner_name"),
        CheckConstraint(
            "status in ('active','paused','done','archived')", name="ck_project_status"
        ),
    )


class FinPayslipRow(Base):
    """One pay period's salary: income components, deductions, and the net that lands."""

    __tablename__ = "fin_payslips"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    payday: Mapped[date] = mapped_column(Date)
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    deductions: Mapped[dict] = mapped_column(JSON, default=dict)
    gross_minor: Mapped[int] = mapped_column(Integer)
    net_minor: Mapped[int] = mapped_column(Integer)
    account_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("fin_accounts.id", ondelete="SET NULL")
    )
    transaction_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("owner_user_id", "period_start", name="uq_fin_payslip_period"),
    )
