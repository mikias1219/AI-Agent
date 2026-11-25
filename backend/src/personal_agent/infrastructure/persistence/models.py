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
    Date,
    DateTime,
    Float,
    ForeignKey,
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
    """Something AURA proposes unprompted; always carries a source citation (spec §9.3)."""

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
    """One AURA object mirrored to one Drive file (contract section 8)."""

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
    # Set when the AURA object was deleted locally. The Drive file is left untouched.
    local_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DriveFolderRow(Base):
    """Cached Drive folder ids by AURA-relative path, so folders are looked up once."""

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
