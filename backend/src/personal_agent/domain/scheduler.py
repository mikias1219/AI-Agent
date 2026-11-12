"""Jobs, reminders and automations (AUT-01, TSK-05)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    MISSED = "missed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Job:
    id: str
    run_at: datetime
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    last_error: str = ""
    idempotency_key: str = ""
    created_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(slots=True)
class Reminder:
    id: str
    owner_user_id: str
    text: str
    remind_at: datetime
    task_id: str | None = None
    channels: list[str] = field(default_factory=lambda: ["inbox"])
    status: ReminderStatus = ReminderStatus.PENDING
    late: bool = False
    delivered_at: datetime | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class Automation:
    id: str
    owner_user_id: str
    kind: str  # daily_briefing
    enabled: bool = True
    # Local time HH:MM in the owner's timezone.
    schedule_time: str = "08:00"
    channels: list[str] = field(default_factory=lambda: ["inbox", "telegram"])
    last_run_at: datetime | None = None
    last_result: str = ""
    last_run_id: str | None = None
    created_at: datetime | None = None


LATE_AFTER_SECONDS = 5 * 60

__all__ = [
    "LATE_AFTER_SECONDS",
    "Automation",
    "Job",
    "JobStatus",
    "Reminder",
    "ReminderStatus",
]
