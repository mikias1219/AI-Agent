"""Repository implementations of the `domain.ports` contracts.

Each repository owns its SQL and its mapping to `domain/models.py` — no other layer
constructs or queries ORM rows.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.approvals import Approval, ApprovalStatus, arguments_hash
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import (
    AgentRun,
    ConversationSummary,
    Message,
    OwnerProfile,
    RunStatus,
    RunStep,
    StepStatus,
    Task,
    TaskPriority,
    TaskStatus,
    ToolCall,
    ToolContext,
)
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import (
    AgentRunRow,
    ApprovalRow,
    AuditEntryRow,
    ConversationRow,
    MessageRow,
    OwnerProfileRow,
    RunStepRow,
    TaskRow,
)

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_LIMIT = 20


# -- conversations -----------------------------------------------------------


class ConversationRepositoryImpl:
    """Implements `domain.ports.ConversationRepository` over SQLAlchemy."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create_session(self, user_id: str) -> str:
        """Persist and return a new conversation id."""
        session_id = uuid.uuid4().hex
        with session_scope(self._factory) as session:
            session.add(ConversationRow(id=session_id, user_id=user_id))
        return session_id

    def append(self, session_id: str, message: Message) -> None:
        """Append one domain message, serializing provider tool calls to JSON."""
        with session_scope(self._factory) as session:
            session.add(
                MessageRow(
                    conversation_id=session_id,
                    role=message.role,
                    content=message.content,
                    name=message.name,
                    tool_call_id=message.tool_call_id,
                    tool_calls_json=json.dumps(
                        [
                            {"id": c.id, "name": c.name, "arguments": c.arguments}
                            for c in message.tool_calls
                        ]
                    ),
                )
            )

    def load(self, session_id: str, limit: int = DEFAULT_HISTORY_LIMIT) -> list[Message]:
        """Load recent history oldest→newest; empty list for unknown sessions."""
        with session_scope(self._factory) as session:
            rows = (
                session.query(MessageRow)
                .filter(MessageRow.conversation_id == session_id)
                .order_by(MessageRow.id.desc())
                .limit(limit)
                .all()
            )
        rows.reverse()
        return [_message_from_row(row) for row in rows]

    def latest_session(self, user_id: str) -> str | None:
        with session_scope(self._factory) as session:
            row = (
                session.query(ConversationRow)
                .filter(ConversationRow.user_id == user_id)
                .order_by(ConversationRow.created_at.desc())
                .first()
            )
            return row.id if row else None

    def list_sessions(self, limit: int = 50) -> list[ConversationSummary]:
        """List conversations newest first without exposing ORM rows to interfaces."""
        with session_scope(self._factory) as session:
            rows = (
                session.query(ConversationRow)
                .order_by(ConversationRow.created_at.desc())
                .limit(limit)
                .all()
            )
        return [
            ConversationSummary(
                id=row.id, user_id=row.user_id, created_at=row.created_at.replace(tzinfo=UTC)
            )
            for row in rows
        ]


def _message_from_row(row: MessageRow) -> Message:
    try:
        raw_calls = json.loads(row.tool_calls_json or "[]")
    except ValueError:
        logger.warning("Skipped malformed tool_calls_json on message id=%s", row.id)
        raw_calls = []
    calls = tuple(
        ToolCall(
            id=str(c.get("id", "")),
            name=str(c.get("name", "")),
            arguments=c.get("arguments") or {},
        )
        for c in raw_calls
        if isinstance(c, dict)
    )
    return Message(
        role=row.role,  # type: ignore[arg-type]  # roles are constrained at write time
        content=row.content,
        name=row.name,
        tool_call_id=row.tool_call_id,
        tool_calls=calls,
    )


# -- tasks -------------------------------------------------------------------


class TaskRepositoryImpl:
    """Implements `domain.ports.TaskRepository` over SQLAlchemy."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, task: Task) -> None:
        """Persist a fresh task."""
        with session_scope(self._factory) as session:
            session.add(TaskRow(**_task_to_row_fields(task)))

    def get(self, task_id: str) -> Task | None:
        """Fetch one task or None — 'not found' is a normal result."""
        with session_scope(self._factory) as session:
            row = session.get(TaskRow, task_id)
            return _task_from_row(row) if row else None

    def list(self, status: TaskStatus | None = None) -> list[Task]:
        """List tasks, optional status filter, newest first."""
        with session_scope(self._factory) as session:
            query = session.query(TaskRow).order_by(TaskRow.created_at.desc())
            if status is not None:
                query = query.filter(TaskRow.status == status.value)
            return [_task_from_row(row) for row in query.all()]

    def save(self, task: Task) -> None:
        """Update an existing task's mutable fields (status, title, ...)."""
        fields = _task_to_row_fields(task)
        with session_scope(self._factory) as session:
            row = session.get(TaskRow, task.id)
            if row is None:
                raise StorageError(f"Cannot save unknown task id={task.id}.")
            for key, value in fields.items():
                setattr(row, key, value)


def _to_utc(value: datetime | None) -> datetime | None:
    """Store instants in UTC: SQLite drops tzinfo, so wall-clock times would be ambiguous."""
    if value is None:
        return None
    return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _from_utc(value: datetime | None) -> datetime | None:
    """Read back as timezone-aware UTC (SQLite returns naive datetimes)."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _task_to_row_fields(task: Task) -> dict[str, Any]:
    """Domain → column mapping, shared by add() and save()."""
    return {
        "id": task.id,
        "owner_user_id": task.owner_user_id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "priority": task.priority.value,
        "due_at": _to_utc(task.due_at),
        "project": task.project,
        "tags": list(task.tags),
        "source": task.source,
        "source_ref": task.source_ref,
        "completed_at": _to_utc(task.completed_at),
        "deleted_at": _to_utc(task.deleted_at),
    }


def _task_from_row(row: TaskRow) -> Task:
    """Column → domain mapping."""
    return Task(
        id=row.id,
        title=row.title,
        description=row.description,
        status=TaskStatus(row.status),
        owner_user_id=row.owner_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        priority=TaskPriority(row.priority or "none"),
        due_at=_from_utc(row.due_at),
        project=row.project or "",
        tags=list(row.tags or []),
        source=row.source or "",
        source_ref=row.source_ref or "",
        completed_at=_from_utc(row.completed_at),
        deleted_at=_from_utc(row.deleted_at),
    )


# -- owner profile -----------------------------------------------------------


def _load_agent_control(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


class OwnerProfileRepositoryImpl:
    """Implements `domain.ports.OwnerProfileRepository` over SQLAlchemy."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def get(self, owner_id: str) -> OwnerProfile | None:
        with session_scope(self._factory) as session:
            row = session.get(OwnerProfileRow, owner_id)
            if row is None:
                return None
            return OwnerProfile(
                owner_id=row.owner_id,
                name=row.name,
                timezone=row.timezone,
                language=row.language,
                wizard_completed=bool(row.wizard_completed),
                checklist=dict(row.checklist or {}),
                agent_control=_load_agent_control(row.agent_control_json),
            )

    def save(self, profile: OwnerProfile) -> None:
        with session_scope(self._factory) as session:
            row = session.get(OwnerProfileRow, profile.owner_id)
            if row is None:
                row = OwnerProfileRow(owner_id=profile.owner_id)
                session.add(row)
            row.name = profile.name
            row.timezone = profile.timezone
            row.language = profile.language
            row.wizard_completed = 1 if profile.wizard_completed else 0
            row.checklist = dict(profile.checklist or {})
            row.agent_control_json = (
                json.dumps(profile.agent_control, sort_keys=True) if profile.agent_control else None
            )
            row.updated_at = datetime.now(UTC)


# -- approvals (implements domain.ports.ApprovalStore) -----------------------------------


def _aware(value: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; every stored timestamp is UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _approval_from_row(row: ApprovalRow) -> Approval:
    return Approval(
        id=row.id,
        tool_name=row.tool_name,
        arguments=json.loads(row.arguments_json or "{}"),
        arguments_hash=row.arguments_hash or "",
        user_id=row.user_id,
        session_id=row.session_id or "",
        origin=row.origin or "",
        run_id=row.run_id,
        call_id=row.call_id or "",
        risk=row.risk or "medium",
        summary=row.summary or "",
        untrusted_content=bool(row.untrusted_content),
        status=ApprovalStatus(row.status),
        created_at=_aware(row.created_at),
        expires_at=_aware(row.expires_at),
        decided_at=_aware(row.decided_at),
        decided_by=row.decided_by or "",
        channel=row.channel or "",
        result=row.result or "",
        edited_from=row.edited_from,
    )


class ApprovalRepositoryImpl:
    """Implements `domain.ports.ApprovalStore` (plus the legacy gateway helpers)."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create(self, approval: Approval) -> None:
        with session_scope(self._factory) as session:
            session.add(
                ApprovalRow(
                    id=approval.id,
                    tool_name=approval.tool_name,
                    arguments_json=json.dumps(approval.arguments, sort_keys=True, default=str),
                    user_id=approval.user_id,
                    session_id=approval.session_id,
                    origin=approval.origin,
                    status=approval.status.value,
                    created_at=approval.created_at or datetime.now(UTC),
                    run_id=approval.run_id,
                    call_id=approval.call_id,
                    arguments_hash=approval.arguments_hash,
                    risk=approval.risk,
                    summary=approval.summary,
                    untrusted_content=int(approval.untrusted_content),
                    expires_at=approval.expires_at,
                    edited_from=approval.edited_from,
                )
            )

    def get(self, approval_id: str) -> Approval | None:
        with session_scope(self._factory) as session:
            row = session.get(ApprovalRow, approval_id)
            return _approval_from_row(row) if row else None

    def find(
        self, status: ApprovalStatus | None = None, run_id: str | None = None, limit: int = 50
    ) -> list[Approval]:
        with session_scope(self._factory) as session:
            query = session.query(ApprovalRow)
            if status is not None:
                query = query.filter(ApprovalRow.status == status.value)
            if run_id is not None:
                query = query.filter(ApprovalRow.run_id == run_id)
            rows = query.order_by(ApprovalRow.created_at.desc()).limit(limit).all()
            return [_approval_from_row(row) for row in rows]

    def list_expired(self, now: datetime) -> list[Approval]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(ApprovalRow)
                .filter(ApprovalRow.status == ApprovalStatus.PENDING.value)
                .filter(ApprovalRow.expires_at.is_not(None))
                .filter(ApprovalRow.expires_at <= now)
                .all()
            )
            return [_approval_from_row(row) for row in rows]

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
        """Single UPDATE ... WHERE status IN (...): exactly one concurrent caller wins."""
        values: dict[str, Any] = {"status": to_status.value}
        if to_status not in (ApprovalStatus.EXECUTED, ApprovalStatus.FAILED):
            values["decided_at"] = now
        if decided_by is not None:
            values["decided_by"] = decided_by
        if channel is not None:
            values["channel"] = channel
        if result is not None:
            values["result"] = result
        with session_scope(self._factory) as session:
            updated = (
                session.query(ApprovalRow)
                .filter(ApprovalRow.id == approval_id)
                .filter(ApprovalRow.status.in_([status.value for status in from_statuses]))
                .update(values, synchronize_session=False)
            )
            return bool(updated)

    # -- helpers kept for the CLI notifier path and older tests -----------------

    def create_pending(self, approval_id: str, call: ToolCall, ctx: ToolContext) -> None:
        """Persist a pending approval without hash or expiry details (legacy helper)."""
        self.create(
            Approval(
                id=approval_id,
                tool_name=call.name,
                arguments=dict(call.arguments),
                arguments_hash=arguments_hash(call.arguments),
                user_id=ctx.user_id,
                session_id=ctx.session_id,
                origin=ctx.origin,
                run_id=ctx.run_id,
                call_id=call.id,
                created_at=datetime.now(UTC),
            )
        )

    def decision(self, approval_id: str) -> str | None:
        """Current status string, or None when unknown."""
        approval = self.get(approval_id)
        return approval.status.value if approval else None

    def update_status(self, approval_id: str, status: str) -> None:
        """Resolve a pending approval once, stamping its decision time."""
        approval = self.get(approval_id)
        if approval is None:
            raise StorageError(f"Unknown approval id={approval_id[:8]}.")
        moved = self.transition(
            approval_id,
            [ApprovalStatus.PENDING],
            ApprovalStatus(status),
            now=datetime.now(UTC),
        )
        if not moved:
            raise StorageError(f"Approval id={approval_id[:8]} is no longer pending.")


# -- agent runs --------------------------------------------------------------


class AgentRunRepositoryImpl:
    """Implements `domain.ports.AgentRunRepository` over SQLAlchemy."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create(self, run: AgentRun) -> None:
        with session_scope(self._factory) as session:
            session.add(AgentRunRow(**_run_fields(run)))

    def get(self, run_id: str) -> AgentRun | None:
        with session_scope(self._factory) as session:
            row = session.get(AgentRunRow, run_id)
            return _run_from_row(row) if row else None

    def save(self, run: AgentRun) -> None:
        with session_scope(self._factory) as session:
            row = session.get(AgentRunRow, run.id)
            if row is None:
                raise StorageError(f"Cannot save unknown run id={run.id[:8]}.")
            for key, value in _run_fields(run).items():
                setattr(row, key, value)

    def list_recent(self, user_id: str | None = None, limit: int = 50) -> list[AgentRun]:
        with session_scope(self._factory) as session:
            query = session.query(AgentRunRow)
            if user_id is not None:
                query = query.filter(AgentRunRow.user_id == user_id)
            rows = query.order_by(AgentRunRow.created_at.desc()).limit(limit).all()
            return [_run_from_row(row) for row in rows]

    def add_step(self, step: RunStep) -> None:
        with session_scope(self._factory) as session:
            session.add(RunStepRow(**_step_fields(step)))

    def save_step(self, step: RunStep) -> None:
        with session_scope(self._factory) as session:
            row = session.get(RunStepRow, step.id)
            if row is None:
                raise StorageError(f"Cannot save unknown run step id={step.id[:8]}.")
            for key, value in _step_fields(step).items():
                setattr(row, key, value)

    def list_steps(self, run_id: str) -> list[RunStep]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(RunStepRow)
                .filter(RunStepRow.run_id == run_id)
                .order_by(RunStepRow.seq)
                .all()
            )
            return [_step_from_row(row) for row in rows]


def _run_fields(run: AgentRun) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "id": run.id,
        "session_id": run.session_id,
        "user_id": run.user_id,
        "origin": run.origin,
        "status": run.status.value,
        "prompt_version": run.prompt_version,
        "model": run.model,
        "trace_id": run.trace_id or "",
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "input_text": run.input_text,
        "final_text": run.final_text,
        "error": run.error,
        "stop_reason": run.stop_reason,
        "finished_at": _to_utc(run.finished_at),
    }
    if run.created_at is not None:
        fields["created_at"] = _to_utc(run.created_at)
    return fields


def _run_from_row(row: AgentRunRow) -> AgentRun:
    return AgentRun(
        id=row.id,
        session_id=row.session_id,
        user_id=row.user_id,
        origin=row.origin,
        status=RunStatus(row.status),
        prompt_version=row.prompt_version,
        model=row.model or "",
        trace_id=getattr(row, "trace_id", None) or "",
        input_tokens=getattr(row, "input_tokens", None),
        output_tokens=getattr(row, "output_tokens", None),
        input_text=row.input_text,
        final_text=row.final_text,
        error=row.error,
        stop_reason=row.stop_reason,
        created_at=_from_utc(row.created_at),
        finished_at=_from_utc(row.finished_at),
    )


def _step_fields(step: RunStep) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "id": step.id,
        "run_id": step.run_id,
        "seq": step.seq,
        "kind": step.kind,
        "name": step.name,
        "status": step.status.value,
        "arguments": dict(step.arguments),
        "output": step.output,
        "error": step.error,
        "result_type": step.result_type or "generic",
        "result_json": dict(step.result_json or {}),
        "finished_at": _to_utc(step.finished_at),
        "duration_ms": step.duration_ms,
    }
    if step.started_at is not None:
        fields["started_at"] = _to_utc(step.started_at)
    return fields


def _step_from_row(row: RunStepRow) -> RunStep:
    return RunStep(
        id=row.id,
        run_id=row.run_id,
        seq=row.seq,
        kind=row.kind,
        name=row.name,
        status=StepStatus(row.status),
        arguments=dict(row.arguments or {}),
        output=row.output,
        error=row.error,
        result_type=getattr(row, "result_type", None) or "generic",
        result_json=dict(getattr(row, "result_json", None) or {}),
        started_at=_from_utc(row.started_at),
        finished_at=_from_utc(row.finished_at),
        duration_ms=row.duration_ms,
    )


# -- audit log ---------------------------------------------------------------


class AuditLogImpl:
    """Append-only implementation of `domain.ports.AuditLog`."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def record(self, event: str, actor: str, details: Mapping[str, Any]) -> None:
        """Append one row; auditing must never crash the caller's flow."""
        try:
            with session_scope(self._factory) as session:
                session.add(AuditEntryRow(actor=actor, event=event, details_json=dict(details)))
        except Exception:  # noqa: BLE001 — audit must never take the app down
            logger.exception("Failed to persist audit event '%s'", event)

    def list_recent(
        self, limit: int = 50, offset: int = 0, events: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Return JSON-friendly recent audit events for local operations views."""
        with session_scope(self._factory) as session:
            query = session.query(AuditEntryRow)
            if events:
                query = query.filter(AuditEntryRow.event.in_(events))
            rows = query.order_by(AuditEntryRow.id.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": row.id,
                "occurred_at": row.occurred_at.replace(tzinfo=UTC).isoformat(),
                "actor": row.actor,
                "event": row.event,
                "details": row.details_json,
            }
            for row in rows
        ]


def recent_audit(factory: sessionmaker[Session], limit: int = 50) -> list[AuditEntryRow]:
    """Read-side helper for debugging/monitoring (used by future ops tooling)."""
    with session_scope(factory) as session:
        return session.query(AuditEntryRow).order_by(AuditEntryRow.id.desc()).limit(limit).all()
