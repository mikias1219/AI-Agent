"""Tick worker: enqueue and run jobs (AUT-01, AUT-02, TSK-05, BR-07, BR-14)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.dates import get_zone
from personal_agent.domain.models import AgentRun, RunStatus
from personal_agent.domain.ports import (
    AgentRunRepository,
    ApprovalStore,
    AuditLog,
    AutomationStore,
    JobQueue,
    ReminderStore,
)
from personal_agent.domain.scheduler import (
    LATE_AFTER_SECONDS,
    Automation,
    Job,
    Reminder,
    ReminderStatus,
)
from personal_agent.domain.task_rules import TaskView

logger = logging.getLogger(__name__)

KIND_REMINDER = "deliver_reminder"
KIND_BRIEFING = "daily_briefing"


class SchedulerService:
    """Schedules reminders and daily briefings; processes the durable job queue."""

    def __init__(
        self,
        *,
        jobs: JobQueue,
        reminders: ReminderStore,
        automations: AutomationStore,
        tasks: TaskService,
        profiles: ProfileService,
        approvals: ApprovalStore | None = None,
        runs: AgentRunRepository | None = None,
        audit: AuditLog | None = None,
        telegram_send: Callable[[str], None] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        owner_id: str = "dashboard",
    ) -> None:
        self._jobs = jobs
        self._reminders = reminders
        self._automations = automations
        self._tasks = tasks
        self._profiles = profiles
        self._approvals = approvals
        self._runs = runs
        self._audit = audit
        self._telegram_send = telegram_send
        self._clock = clock
        self._owner_id = owner_id

    def tick(self) -> dict[str, Any]:
        """Enqueue due work and process claimed jobs. Safe to call concurrently (idempotent)."""
        now = self._clock()
        enqueued_reminders = self.enqueue_due_reminders(now)
        enqueued_briefings = self.enqueue_due_briefings(now)
        processed = self.process_due_jobs(now)
        return {
            "enqueued_reminders": enqueued_reminders,
            "enqueued_briefings": enqueued_briefings,
            "processed": processed,
            "at": now.isoformat(),
        }

    def enqueue_due_reminders(self, now: datetime | None = None) -> int:
        now = now or self._clock()
        count = 0
        for reminder in self._reminders.due(now):
            key = f"reminder:{reminder.id}:deliver"
            self._jobs.enqueue(
                Job(
                    id=uuid.uuid4().hex,
                    run_at=reminder.remind_at,
                    kind=KIND_REMINDER,
                    payload={"reminder_id": reminder.id},
                    idempotency_key=key,
                )
            )
            count += 1
        return count

    def enqueue_due_briefings(self, now: datetime | None = None) -> int:
        now = now or self._clock()
        count = 0
        self._automations.ensure_defaults(self._owner_id)
        for automation in self._automations.list(self._owner_id):
            if not automation.enabled or automation.kind != KIND_BRIEFING:
                continue
            if not self._briefing_due(automation, now):
                continue
            day = now.astimezone(get_zone(self._profiles.timezone_for(self._owner_id))).date()
            key = f"briefing:{self._owner_id}:{day.isoformat()}"
            self._jobs.enqueue(
                Job(
                    id=uuid.uuid4().hex,
                    run_at=now,
                    kind=KIND_BRIEFING,
                    payload={"automation_id": automation.id, "owner_id": self._owner_id},
                    idempotency_key=key,
                )
            )
            count += 1
        return count

    def process_due_jobs(self, now: datetime | None = None, *, limit: int = 20) -> int:
        now = now or self._clock()
        claimed = self._jobs.claim_due(now, limit=limit)
        done = 0
        for job in claimed:
            try:
                self._run_job(job, now)
                self._jobs.mark_done(job.id, now=now)
                done += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("Job %s (%s) failed", job.id, job.kind)
                retry_at = now + timedelta(minutes=min(30, 2 ** min(job.attempts, 4)))
                self._jobs.mark_failed(job.id, error=str(exc), now=now, retry_at=retry_at)
        return done

    def create_reminder(
        self,
        *,
        text: str,
        remind_at: datetime,
        owner_user_id: str,
        task_id: str | None = None,
        channels: list[str] | None = None,
    ) -> Reminder:
        reminder = Reminder(
            id=uuid.uuid4().hex,
            owner_user_id=owner_user_id,
            text=text.strip(),
            remind_at=remind_at,
            task_id=task_id,
            channels=channels or ["inbox", "telegram"],
            status=ReminderStatus.PENDING,
            created_at=self._clock(),
        )
        if not reminder.text:
            raise ValueError("Reminder text is required.")
        self._reminders.add(reminder)
        self._jobs.enqueue(
            Job(
                id=uuid.uuid4().hex,
                run_at=reminder.remind_at,
                kind=KIND_REMINDER,
                payload={"reminder_id": reminder.id},
                idempotency_key=f"reminder:{reminder.id}:deliver",
            )
        )
        if self._audit:
            self._audit.record(
                "reminder.created",
                owner_user_id,
                {"id": reminder.id, "remind_at": reminder.remind_at.isoformat()},
            )
        return reminder

    def _run_job(self, job: Job, now: datetime) -> None:
        if job.kind == KIND_REMINDER:
            self._deliver_reminder(str(job.payload.get("reminder_id", "")), now)
        elif job.kind == KIND_BRIEFING:
            self._run_briefing(
                str(job.payload.get("automation_id", "")),
                str(job.payload.get("owner_id", self._owner_id)),
                now,
            )
        else:
            raise ValueError(f"Unknown job kind '{job.kind}'")

    def _deliver_reminder(self, reminder_id: str, now: datetime) -> None:
        reminder = self._reminders.get(reminder_id)
        if reminder is None:
            return
        if reminder.status is not ReminderStatus.PENDING:
            return  # idempotent: already delivered
        late = (now - reminder.remind_at).total_seconds() > LATE_AFTER_SECONDS
        body = reminder.text
        if late:
            body = f"[late] {body}"
        if "telegram" in reminder.channels and self._telegram_send is not None:
            self._telegram_send(body)
        reminder.status = ReminderStatus.SENT
        reminder.late = late
        reminder.delivered_at = now
        self._reminders.save(reminder)
        if self._audit:
            self._audit.record(
                "reminder.delivered",
                reminder.owner_user_id,
                {"id": reminder.id, "late": late},
            )

    def _run_briefing(self, automation_id: str, owner_id: str, now: datetime) -> None:
        automation = self._automations.get(automation_id)
        if automation is None or not automation.enabled:
            return
        text, run_id = self._build_briefing(owner_id, now)
        for channel in automation.channels:
            if channel == "telegram" and self._telegram_send is not None:
                self._telegram_send(text)
            # inbox: persisted via automation.last_result + audit; Today reads last briefing
        automation.last_run_at = now
        automation.last_result = text
        automation.last_run_id = run_id
        self._automations.save(automation)
        if self._audit:
            self._audit.record(
                "automation.briefing",
                owner_id,
                {"automation_id": automation_id, "run_id": run_id},
            )

    def _build_briefing(self, owner_id: str, now: datetime) -> tuple[str, str | None]:
        timezone = self._profiles.timezone_for(owner_id)
        local = now.astimezone(get_zone(timezone))
        lines = [
            f"Daily briefing — {local.strftime('%A %d %B %Y')}",
            "",
            "Calendar: nothing scheduled.",
            "",
        ]
        due = self._tasks.list(view=TaskView.TODAY, timezone=timezone, owner_user_id=owner_id)
        overdue = self._tasks.list(view=TaskView.OVERDUE, timezone=timezone, owner_user_id=owner_id)
        if not due and not overdue:
            lines.append("Tasks: nothing due today.")
        else:
            if overdue:
                lines.append("Overdue:")
                lines.extend(f"- {task.title}" for task in overdue[:10])
            if due:
                lines.append("Due today:")
                lines.extend(f"- {task.title}" for task in due[:10])
        lines.append("")
        pending = 0
        if self._approvals is not None:
            from personal_agent.domain.approvals import ApprovalStatus

            pending = len(self._approvals.find(status=ApprovalStatus.PENDING, limit=50))
        lines.append(f"Pending approvals: {pending}." if pending else "Pending approvals: none.")
        text = "\n".join(lines)
        run_id = None
        if self._runs is not None:
            run = AgentRun(
                id=uuid.uuid4().hex,
                session_id="",
                user_id=owner_id,
                origin="automation",
                prompt_version="briefing_v1",
                status=RunStatus.COMPLETED,
                input_text="daily_briefing",
                final_text=text,
                model="scheduler",
                created_at=now,
                finished_at=now,
            )
            self._runs.create(run)
            run_id = run.id
        return text, run_id

    def _briefing_due(self, automation: Automation, now: datetime) -> bool:
        timezone = self._profiles.timezone_for(automation.owner_user_id)
        local = now.astimezone(get_zone(timezone))
        try:
            hour_s, minute_s = automation.schedule_time.split(":", 1)
            hour, minute = int(hour_s), int(minute_s)
        except ValueError:
            hour, minute = 8, 0
        scheduled = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if local < scheduled:
            return False
        if automation.last_run_at is None:
            return True
        last_local = automation.last_run_at.astimezone(get_zone(timezone))
        return last_local.date() < local.date()

    def latest_briefing(self, owner_id: str) -> str | None:
        self._automations.ensure_defaults(owner_id)
        for automation in self._automations.list(owner_id):
            if automation.kind == KIND_BRIEFING and automation.last_result:
                return automation.last_result
        return None

    def run_automation_now(self, automation_id: str, owner_id: str) -> dict[str, Any]:
        automation = self._automations.get(automation_id)
        if automation is None or automation.owner_user_id != owner_id:
            raise ValueError("Unknown automation.")
        now = self._clock()
        key = f"briefing:{owner_id}:manual:{uuid.uuid4().hex}"
        self._jobs.enqueue(
            Job(
                id=uuid.uuid4().hex,
                run_at=now,
                kind=KIND_BRIEFING,
                payload={"automation_id": automation.id, "owner_id": owner_id},
                idempotency_key=key,
            )
        )
        processed = self.process_due_jobs(now)
        refreshed = self._automations.get(automation_id)
        return {"processed": processed, "automation": refreshed}


__all__ = ["KIND_BRIEFING", "KIND_REMINDER", "SchedulerService"]
