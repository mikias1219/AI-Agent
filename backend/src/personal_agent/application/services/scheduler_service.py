"""Tick worker: enqueue and run jobs (AUT-01, AUT-02, TSK-05, BR-07, BR-14)."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from personal_agent.application.services.agent_control_service import AgentControlService
from personal_agent.application.services.briefing_builder import BriefingBuilder, BriefingDocument
from personal_agent.application.services.proactive_gate import decide_proactive_send
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.routine_catalog import catalogue_by_kind
from personal_agent.application.services.routine_runner import RoutineRunner
from personal_agent.application.services.suggestion_service import SuggestionService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.dates import get_zone
from personal_agent.domain.life import NotificationPolicy
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
# Job kinds that run an Automation row (briefing or catalogue routine).
AUTOMATION_JOB_KINDS = frozenset(
    {
        "daily_briefing",
        "inbox_triage",
        "evening_wrapup",
        "weekly_review",
        "deadline_guard",
        "learning_daily",
        "reading_daily",
        "diary_nudge",
        "habit_nudge",
        "money_alerts",
        "daily_wrapup",
    }
)


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
        routine_runner: RoutineRunner | None = None,
        suggestions: SuggestionService | None = None,
        notification_policy: Callable[[str], NotificationPolicy] | None = None,
    ) -> None:
        self._notification_policy = notification_policy
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
        self._routine_runner = routine_runner
        self._suggestions = suggestions

    def tick(self) -> dict[str, Any]:
        """Enqueue due work and process claimed jobs. Safe to call concurrently (idempotent)."""
        now = self._clock()
        enqueued_reminders = self.enqueue_due_reminders(now)
        enqueued_briefings = self.enqueue_due_automations(now)
        processed = self.process_due_jobs(now)
        result = {
            "enqueued_reminders": enqueued_reminders,
            "enqueued_briefings": enqueued_briefings,
            "enqueued_automations": enqueued_briefings,
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
        """Backward-compatible alias: enqueues every due automation, not only briefing."""
        return self.enqueue_due_automations(now)

    def enqueue_due_automations(self, now: datetime | None = None) -> int:
        now = now or self._clock()
        count = 0
        self._automations.ensure_defaults(self._owner_id)
        day = now.astimezone(get_zone(self._profiles.timezone_for(self._owner_id))).date()
        for automation in self._automations.list(self._owner_id):
            if not automation.enabled:
                continue
            if automation.kind not in AUTOMATION_JOB_KINDS:
                continue
            if not self._automation_due(automation, now):
                continue
            key = f"automation:{automation.kind}:{self._owner_id}:{day.isoformat()}"
            self._jobs.enqueue(
                Job(
                    id=uuid.uuid4().hex,
                    run_at=now,
                    kind=automation.kind,
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
        elif job.kind in AUTOMATION_JOB_KINDS:
            self._run_automation(
                str(job.payload.get("automation_id", "")),
                str(job.payload.get("owner_id", self._owner_id)),
                now,
                kind=job.kind,
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
        policy = self._policy(reminder.owner_user_id)
        if (
            "telegram" in reminder.channels
            and self._telegram_send is not None
            and policy.telegram
            and policy.reminders
        ):
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

    def _run_automation(
        self, automation_id: str, owner_id: str, now: datetime, *, kind: str
    ) -> None:
        automation = self._automations.get(automation_id)
        if automation is None or not automation.enabled:
            return
        spec = catalogue_by_kind().get(kind)
        if kind == KIND_BRIEFING or (spec is not None and spec.uses_briefing_builder):
            self._run_briefing(automation, owner_id, now)
            return
        if self._routine_runner is None:
            raise RuntimeError("RoutineRunner is not configured.")
        result = self._routine_runner.run(automation, now)
        if result.get("nudge"):
            result["delivered"] = self._deliver_nudge(
                automation, owner_id, str(result["nudge"]), now
            )
        automation.last_run_at = now
        automation.last_result = str(
            result.get("summary") or json.dumps(result, ensure_ascii=False)
        )
        automation.last_run_id = result.get("run_id")
        self._automations.save(automation)
        if self._audit:
            self._audit.record(
                "automation.routine",
                owner_id,
                {
                    "automation_id": automation_id,
                    "kind": kind,
                    "run_id": automation.last_run_id,
                    "proposed": result.get("proposed"),
                },
            )

    def _policy(self, owner_id: str) -> NotificationPolicy:
        return (
            self._notification_policy(owner_id)
            if self._notification_policy is not None
            else NotificationPolicy()
        )

    def _deliver_nudge(
        self, automation: Automation, owner_id: str, text: str, now: datetime
    ) -> list[str]:
        """Deliver a life nudge like the briefing: in-app as a suggestion, Telegram via the gate."""
        policy = self._policy(owner_id)
        delivered: list[str] = []
        if policy.in_app and self._suggestions is not None:
            try:
                self._suggestions.create(
                    owner_id,
                    kind="followup",
                    title=text[:240],
                    reason="Your daily routine is on.",
                    source=f"routine:{automation.kind}",
                    proposed_action={},
                    expires_in=timedelta(days=1),
                    origin="automation",
                )
                delivered.append("in_app")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Nudge suggestion failed: %s", exc)
        if policy.telegram and self._telegram_send is not None:
            if self._allow_external_proactive(owner_id, now):
                self._telegram_send(text)
                delivered.append("telegram")
                if self._agent_control is not None:
                    self._agent_control.record_proactive(owner_id)
            elif self._audit:
                self._audit.record(
                    "automation.proactive_blocked", owner_id, {"automation_id": automation.id}
                )
        return delivered

    def _run_briefing(self, automation: Automation, owner_id: str, now: datetime) -> None:
        doc = self._build_briefing(owner_id, now)
        telegram_sent = False
        for channel in automation.channels:
            if (
                channel == "telegram"
                and self._telegram_send is not None
                and self._policy(owner_id).telegram
            ):
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
                        {"automation_id": automation.id},
                    )
        self._propose_from_briefing(owner_id, doc)
        automation.last_run_at = now
        automation.last_result = doc.to_json()
        automation.last_run_id = doc.run_id
        self._automations.save(automation)
        if self._audit:
            self._audit.record(
                "automation.briefing",
                owner_id,
                {
                    "automation_id": automation.id,
                    "run_id": doc.run_id,
                    "telegram_sent": telegram_sent,
                },
            )

    def _propose_from_briefing(self, owner_id: str, doc: BriefingDocument) -> None:
        """Create at most two follow-up suggestions from briefing sections (G1)."""
        if self._suggestions is None:
            return
        if len(self._suggestions.open(owner_id)) >= 5:
            return
        proposed = 0
        for section in doc.sections:
            if proposed >= 2:
                break
            if section.status != "ok" or not section.items:
                continue
            if section.id not in {"email", "tasks", "approvals"}:
                continue
            first = section.items[0]
            kind = (
                "followup"
                if section.id == "email"
                else "deadline"
                if section.id == "tasks"
                else "followup"
            )
            title = {
                "email": f"Review email: {first.title}",
                "tasks": f"Work on: {first.title}",
                "approvals": "Clear pending approvals",
            }.get(section.id, first.title)
            try:
                self._suggestions.create(
                    owner_id,
                    kind=kind,
                    title=title,
                    reason=section.summary or first.detail or first.title,
                    source=f"briefing:{section.id}",
                    proposed_action={},
                    expires_in=timedelta(days=1),
                    origin="automation",
                )
                proposed += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Briefing suggestion failed: %s", exc)

    def proactive_allowed(self, automation: Automation, now: datetime) -> bool:
        """Quiet hours, pause and daily cap for a routine's own output (BR-14)."""
        return self._allow_external_proactive(
            automation.owner_user_id,
            now,
            quiet_hours_start=automation.quiet_hours_start,
            quiet_hours_end=automation.quiet_hours_end,
            daily_cap=automation.daily_cap,
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
        policy = self._policy(owner_id)
        if not (quiet_hours_start and quiet_hours_end) and policy.quiet_enabled:
            quiet_hours_start, quiet_hours_end = policy.quiet_start, policy.quiet_end
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

    def _automation_due(self, automation: Automation, now: datetime) -> bool:
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
        # Weekly review: once per ISO week.
        if automation.kind == "weekly_review":
            if automation.last_run_at is None:
                return local.weekday() == 0  # Monday
            last_local = automation.last_run_at.astimezone(get_zone(timezone))
            return last_local.isocalendar()[:2] < local.isocalendar()[:2] and local.weekday() == 0
        if automation.last_run_at is None:
            return True
        last_local = automation.last_run_at.astimezone(get_zone(timezone))
        return last_local.date() < local.date()

    def _briefing_due(self, automation: Automation, now: datetime) -> bool:
        return self._automation_due(automation, now)

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
        if automation.kind not in AUTOMATION_JOB_KINDS:
            raise ValueError(f"Unknown automation kind '{automation.kind}'.")
        now = self._clock()
        key = f"automation:{automation.kind}:{owner_id}:manual:{uuid.uuid4().hex}"
        self._jobs.enqueue(
            Job(
                id=uuid.uuid4().hex,
                run_at=now,
                kind=automation.kind,
                payload={"automation_id": automation.id, "owner_id": owner_id},
                idempotency_key=key,
            )
        )
        processed = self.process_due_jobs(now)
        refreshed = self._automations.get(automation_id)
        return {"processed": processed, "automation": refreshed}


__all__ = ["AUTOMATION_JOB_KINDS", "KIND_BRIEFING", "KIND_REMINDER", "SchedulerService"]
