"""Google Calendar events for timed tasks (contract section 9, ADR 0035).

Calendar is a *view* of tasks: events cannot hold a done state, so AURA stays the source of
truth. A completed task's event is updated on the next sync (summary prefix and description).
Like the Drive backup, a run goes through the tool registry (`task_calendar_sync`): one
approval for the whole batch with mode `ask`, immediate with mode `auto`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.sync_common import (
    CALENDAR_EVENTS_SCOPE,
    READ_ONLY_MESSAGE,
    SyncUnavailable,
    mode_label,
    run_batch,
    scope_granted,
)
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.days import effective_outcome
from personal_agent.domain.exceptions import IntegrationError
from personal_agent.domain.life import LifeError
from personal_agent.domain.models import Task, TaskStatus
from personal_agent.domain.ports import AuditLog, SyncSettingsStore, ToolRegistry
from personal_agent.domain.task_rules import has_time_of_day, local_date

logger = logging.getLogger(__name__)

NOT_CONNECTED = "Google Calendar is not connected."
RECONNECT = "Reconnect Google to allow Calendar sync."
SERVICE = "calendar"
TOOL = "task_calendar_sync"
MAX_BATCH = 25
EVENT_MINUTES = 30
PREFIXES = {"achieved": "✓ ", "partial": "◐ ", "missed": "✗ ", "skipped": "– "}
_ABORT_STATUSES = (401, 403)
_GONE_STATUSES = (404, 410)


class CalendarClient(Protocol):
    def create_calendar_event(
        self,
        *,
        title: str,
        starts_at: str,
        ends_at: str,
        location: str = "",
        description: str = "",
        all_day: bool = False,
    ) -> dict[str, Any]: ...

    def update_calendar_event(
        self,
        *,
        event_id: str,
        title: str | None = None,
        starts_at: str | None = None,
        ends_at: str | None = None,
        location: str | None = None,
        description: str | None = None,
        all_day: bool = False,
    ) -> dict[str, Any]: ...


def event_title(task: Task) -> str:
    """Task title with the outcome prefix (open tasks have none)."""
    if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
        return PREFIXES.get(effective_outcome(task) or "", "") + task.title
    return task.title


def event_description(task: Task) -> str:
    lines: list[str] = []
    if task.description.strip():
        lines.append(task.description.strip())
    outcome = (
        effective_outcome(task) if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED) else None
    )
    if outcome:
        lines.append(f"Outcome: {outcome}")
        if task.actual_value is not None or task.target_value is not None:
            actual = _num(task.actual_value) if task.actual_value is not None else "?"
            target = f"/{_num(task.target_value)}" if task.target_value is not None else ""
            unit = f" {task.target_unit}" if task.target_unit else ""
            lines.append(f"{actual}{target}{unit}")
        if task.outcome_note.strip():
            lines.append(task.outcome_note.strip())
    lines.append("Managed by AURA.")
    return "\n".join(lines)


def _num(value: float | None) -> str:
    if value is None:
        return ""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


class CalendarSyncService:
    def __init__(
        self,
        *,
        tasks: TaskService,
        settings: SyncSettingsStore,
        profiles: ProfileService,
        client: CalendarClient,
        registry: ToolRegistry,
        google_status: Callable[[], Mapping[str, Any]],
        approval_required: Callable[[], bool],
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._tasks = tasks
        self._settings = settings
        self._profiles = profiles
        self._client = client
        self._registry = registry
        self._google_status = google_status
        self._approval_required = approval_required
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    # -- state ---------------------------------------------------------------------------

    def connection(self) -> tuple[bool, bool, bool]:
        status = self._google_status()
        return (
            bool(status.get("connected")),
            scope_granted(status, CALENDAR_EVENTS_SCOPE),
            bool(status.get("read_only", True)),
        )

    def require_ready(self) -> None:
        connected, granted, read_only = self.connection()
        if not connected:
            raise SyncUnavailable(NOT_CONNECTED)
        if not granted:
            raise SyncUnavailable(RECONNECT)
        if read_only:
            raise SyncUnavailable(READ_ONLY_MESSAGE)

    def mode(self) -> str:
        return mode_label(self._approval_required())

    def status(self, owner: str) -> dict[str, Any]:
        connected, granted, _ro = self.connection()
        settings = self._settings.get(owner, SERVICE)
        return {
            "connected": connected,
            "scope_granted": granted,
            "enabled": settings.enabled,
            "mode": self.mode(),
            "last_sync_at": settings.last_sync_at.isoformat() if settings.last_sync_at else None,
            "last_error": settings.last_error or None,
            "pending": len(self.pending(owner)),
        }

    def update_settings(self, owner: str, *, enabled: bool | None) -> dict[str, Any]:
        current = self._settings.get(owner, SERVICE)
        if enabled is not None:
            if not isinstance(enabled, bool):
                raise LifeError("enabled must be true or false.")
            current.enabled = enabled
            self._settings.save(current)
            if self._audit is not None:
                self._audit.record("calendar_sync.settings_updated", owner, {"enabled": enabled})
        return self.status(owner)

    # -- pending ----------------------------------------------------------------------------

    def _is_pushable(self, task: Task, tz: str, *, all_day: bool) -> bool:
        return has_time_of_day(task.due_at, tz) or (all_day and task.plan_date is not None)

    def pending(self, owner: str, *, all_day: bool = False) -> list[Task]:
        """Tasks whose event must be created or brought up to date, oldest first."""
        tz = self._profiles.timezone_for(owner)
        today = local_date(self._clock(), tz)
        found: list[Task] = []
        for task in self._tasks.list(owner_user_id=owner):
            if task.is_deleted:
                continue
            if task.calendar_event_id:
                if task.calendar_synced_at is None or (
                    task.updated_at is not None
                    and _aware(task.updated_at) > _aware(task.calendar_synced_at)
                ):
                    found.append(task)
                continue
            if task.status is TaskStatus.CANCELLED:
                continue
            if task.plan_date is not None and task.plan_date < today - timedelta(days=1):
                continue
            if self._is_pushable(task, tz, all_day=all_day):
                found.append(task)
        found.sort(
            key=lambda t: (_aware(t.due_at) if t.due_at else datetime.max.replace(tzinfo=UTC), t.id)
        )
        return found

    def request_run(
        self, owner: str, *, origin: str = "dashboard", all_day: bool = False
    ) -> dict[str, Any]:
        self.require_ready()
        chosen = self.pending(owner, all_day=all_day)[:MAX_BATCH]
        if not chosen:
            return {"status": "nothing_to_do", "approval_id": None, "summary": None}
        arguments: dict[str, Any] = {"task_ids": [t.id for t in chosen]}
        arguments["titles"] = [t.title[:120] for t in chosen]
        if all_day:
            arguments["all_day"] = True
        return run_batch(
            self._registry,
            owner=owner,
            origin=origin,
            session="calendar-sync",
            tool=TOOL,
            arguments=arguments,
        )

    # -- executing (the tool handler) -------------------------------------------------------------

    def execute(
        self, owner: str, task_ids: Sequence[str], *, all_day: bool = False
    ) -> dict[str, Any]:
        self.require_ready()
        if len(task_ids) > MAX_BATCH:
            raise LifeError(f"A Calendar batch holds at most {MAX_BATCH} tasks.")
        tz = self._profiles.timezone_for(owner)
        now = self._clock()
        counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
        errors: list[str] = []
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task is None or task.owner_user_id != owner:
                counts["failed"] += 1
                errors.append(f"{task_id}: task not found")
                continue
            if not self._is_pushable(task, tz, all_day=all_day) and not task.calendar_event_id:
                counts["skipped"] += 1  # date-only task without all_day: never pushed
                continue
            try:
                counts[self._sync_one(task, tz, all_day, now)] += 1
            except IntegrationError as exc:
                if exc.status_code in _ABORT_STATUSES:
                    self._remember(owner, now, str(exc), ok=False)
                    raise
                counts["failed"] += 1
                errors.append(f"{task.title[:60]}: {exc}")
        self._remember(owner, now, errors[0] if errors else "", ok=counts["failed"] == 0)
        if self._audit is not None:
            self._audit.record(
                "calendar_sync.pushed", owner, {**counts, "task_ids": list(task_ids)}
            )
        summary = (
            f"Calendar sync: {counts['created']} created, {counts['updated']} updated, "
            f"{counts['skipped']} skipped, {counts['failed']} failed."
        )
        return {"result_type": "calendar_sync", "summary": summary, **counts, "errors": errors[:10]}

    def _times(self, task: Task, tz: str, all_day: bool) -> tuple[str, str, bool] | None:
        """(starts_at, ends_at, all_day) for the event, or None to leave the time alone."""
        if has_time_of_day(task.due_at, tz) and task.due_at is not None:
            start = task.due_at.astimezone(UTC)
            end = start + timedelta(minutes=EVENT_MINUTES)
            return (
                start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                False,
            )
        if all_day and task.plan_date is not None:
            day: date = task.plan_date
            return day.isoformat(), (day + timedelta(days=1)).isoformat(), True
        return None

    def _sync_one(self, task: Task, tz: str, all_day: bool, now: datetime) -> str:
        times = self._times(task, tz, all_day)
        title = event_title(task)
        description = event_description(task)
        if task.calendar_event_id:
            try:
                self._client.update_calendar_event(
                    event_id=task.calendar_event_id,
                    title=title,
                    starts_at=times[0] if times else None,
                    ends_at=times[1] if times else None,
                    description=description,
                    all_day=times[2] if times else False,
                )
            except IntegrationError as exc:
                if exc.status_code not in _GONE_STATUSES or times is None:
                    raise
                # The owner deleted the event in Google Calendar: create it again.
            else:
                self._tasks.set_calendar_link(task.id, task.calendar_event_id, now)
                return "updated"
        if times is None:
            return "skipped"
        created = self._client.create_calendar_event(
            title=title,
            starts_at=times[0],
            ends_at=times[1],
            description=description,
            all_day=times[2],
        )
        event_id = str(created.get("id") or "")
        if not event_id:
            raise IntegrationError("Google did not return an event id.")
        self._tasks.set_calendar_link(task.id, event_id, now)
        return "created"

    def _remember(self, owner: str, when: datetime, error: str, *, ok: bool) -> None:
        settings = self._settings.get(owner, SERVICE)
        if ok:
            settings.last_sync_at = when
        settings.last_error = error[:500]
        self._settings.save(settings)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
