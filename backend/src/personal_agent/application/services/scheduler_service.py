"""Tick worker: enqueue and run jobs (AUT-01, AUT-02, TSK-05, BR-07, BR-14)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from personal_agent.application.services.agent_control_service import AgentControlService
from personal_agent.application.services.briefing_builder import BriefingBuilder, BriefingDocument
from personal_agent.application.services.proactive_gate import decide_proactive_send
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.dates import get_zone
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
        briefing_builder: BriefingBuilder | None = None,
        agent_control: AgentControlService | None = None,
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
        self._briefing_builder = briefing_builder
        self._agent_control = agent_control

    def tick(self) -> dict[str, Any]:
        """Enqueue due work and process claimed jobs. Safe to call concurrently (idempotent)."""
        now = self._clock()
        enqueued_reminders = self.enqueue_due_reminders(now)
        enqueued_briefings = self.enqueue_due_briefings(now)
        processed = self.process_due_jobs(now)
        result = {
            "enqueued_reminders": enqueued_reminders,
            "enqueued_briefings": enqueued_briefings,
            "processed": processed,
            "at": now.isoformat(),
        }
        if self._audit is not None:
            self._audit.record("scheduler.tick", self._owner_id, dict(result))
        return result

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

    def list_reminders(
        self, owner_user_id: str, *, status: ReminderStatus | None = None, limit: int = 50
    ) -> list[Reminder]:
        return list(self._reminders.list(owner_user_id, status=status, limit=limit))

    def cancel_reminder(self, reminder_id: str, owner_user_id: str) -> Reminder | None:
        reminder = self._reminders.get(reminder_id)
        if reminder is None or reminder.owner_user_id != owner_user_id:
            return None
        if reminder.status is ReminderStatus.CANCELLED:
            return reminder
        reminder.status = ReminderStatus.CANCELLED
        self._reminders.save(reminder)
        if self._audit:
            self._audit.record("reminder.cancelled", owner_user_id, {"id": reminder_id})
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
        telegram_sent = False
        if "telegram" in reminder.channels and self._telegram_send is not None:
            if self._allow_external_proactive(reminder.owner_user_id, now):
                self._telegram_send(body)
                telegram_sent = True
                if self._agent_control is not None:
                    self._agent_control.record_proactive(reminder.owner_user_id)
            elif self._audit:
                self._audit.record(
                    "reminder.proactive_blocked",
                    reminder.owner_user_id,
                    {"id": reminder.id},
                )
        reminder.status = ReminderStatus.SENT
        reminder.late = late
        reminder.delivered_at = now
        self._reminders.save(reminder)
        if self._audit:
            self._audit.record(
                "reminder.delivered",
                reminder.owner_user_id,
                {"id": reminder.id, "late": late, "telegram_sent": telegram_sent},
            )

    def _run_briefing(self, automation_id: str, owner_id: str, now: datetime) -> None:
        automation = self._automations.get(automation_id)
        if automation is None or not automation.enabled:
            return
        doc = self._build_briefing(owner_id, now)
        telegram_sent = False
        for channel in automation.channels:
            if channel == "telegram" and self._telegram_send is not None:
                if self._allow_external_proactive(
                    owner_id,
                    now,
                    quiet_hours_start=automation.quiet_hours_start,
                    quiet_hours_end=automation.quiet_hours_end,
                    daily_cap=automation.daily_cap,
                ):
                    self._telegram_send(doc.text)
                    telegram_sent = True
                    if self._agent_control is not None:
                        self._agent_control.record_proactive(owner_id)
                elif self._audit:
                    self._audit.record(
                        "automation.proactive_blocked",
                        owner_id,
                        {"automation_id": automation_id},
                    )
            # inbox: persisted via automation.last_result + audit; Today reads last briefing
        automation.last_run_at = now
        automation.last_result = doc.to_json()
        automation.last_run_id = doc.run_id
        self._automations.save(automation)
        if self._audit:
            self._audit.record(
                "automation.briefing",
                owner_id,
                {
                    "automation_id": automation_id,
                    "run_id": doc.run_id,
                    "telegram_sent": telegram_sent,
                },
            )

    def _allow_external_proactive(
        self,
        owner_id: str,
        now: datetime,
        *,
        quiet_hours_start: str = "",
        quiet_hours_end: str = "",
        daily_cap: int = 0,
    ) -> bool:
        timezone = self._profiles.timezone_for(owner_id)
        local = now.astimezone(get_zone(timezone))
        if self._agent_control is None:
            decision = decide_proactive_send(
                local_now=local,
                paused=False,
                quiet_hours_start=quiet_hours_start or None,
                quiet_hours_end=quiet_hours_end or None,
                proactive_used=0,
                proactive_cap=daily_cap if daily_cap > 0 else 10_000,
            )
            return decision.allowed
        state = self._agent_control.get(owner_id)
        cap = daily_cap if daily_cap > 0 else int(state.budgets.get("proactive_cap", 3))
        decision = decide_proactive_send(
            local_now=local,
            paused=state.paused,
            quiet_hours_start=quiet_hours_start or None,
            quiet_hours_end=quiet_hours_end or None,
            proactive_used=int(state.budgets.get("proactive_used", 0)),
            proactive_cap=cap,
        )
        return decision.allowed

    def _build_briefing(self, owner_id: str, now: datetime) -> BriefingDocument:
        if self._briefing_builder is None:
            raise RuntimeError("BriefingBuilder is not configured.")
        return self._briefing_builder.build(owner_id, now)

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
        doc = self.latest_briefing_document(owner_id)
        return doc.text if doc else None

    def latest_briefing_document(self, owner_id: str) -> BriefingDocument | None:
        self._automations.ensure_defaults(owner_id)
        for automation in self._automations.list(owner_id):
            if automation.kind == KIND_BRIEFING and automation.last_result:
                return BriefingDocument.from_stored(automation.last_result)
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
