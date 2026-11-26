"""Time tracking (P2-2): timer and manual entries per task, project or goal."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

MAX_MANUAL_MINUTES = 24 * 60
NOTE_MAX = 300


@dataclass(slots=True)
class TimeEntry:
    id: str
    owner_user_id: str
    started_at: datetime
    ended_at: datetime | None = None
    task_id: str | None = None
    goal_id: str | None = None
    project: str = ""
    note: str = ""
    source: str = "timer"

    def minutes(self, now: datetime) -> int:
        end = self.ended_at or now
        return max(0, int((end - self.started_at).total_seconds() // 60))


class TimeRepository(Protocol):
    def add(self, entry: TimeEntry) -> None: ...
    def get(self, owner: str, entry_id: str) -> TimeEntry | None: ...
    def save(self, entry: TimeEntry) -> None: ...
    def delete(self, owner: str, entry_id: str) -> bool: ...
    def running(self, owner: str) -> TimeEntry | None: ...
    def between(self, owner: str, start: datetime, end: datetime) -> Sequence[TimeEntry]: ...
