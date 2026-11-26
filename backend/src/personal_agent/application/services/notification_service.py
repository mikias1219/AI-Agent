"""Notification preferences (contract section 5).

Flags and times that map to a routine (briefing, learning, reading, diary) are stored on the
routine's automation row, so the Automations page and this API never disagree. Channel,
reminder and quiet-hour settings live on the owner profile and are applied by the scheduler's
proactive gate (see `SchedulerService`).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.domain.life import LifeError, NotificationPolicy, valid_hhmm
from personal_agent.domain.ports import AuditLog, AutomationStore
from personal_agent.domain.scheduler import Automation

# key -> automation kind (the routine the flag switches on or off)
_FLAG_KINDS = {
    "daily_briefing": "daily_briefing",
    "learning_daily": "learning_daily",
    "reading_daily": "reading_daily",
    "diary_nudge": "diary_nudge",
    "habit_nudge": "habit_nudge",
    "money_alerts": "money_alerts",
    "daily_wrapup": "daily_wrapup",
}
_TIME_KINDS = {
    "learning_time": "learning_daily",
    "reading_time": "reading_daily",
    "diary_time": "diary_nudge",
    "habit_time": "habit_nudge",
    "money_time": "money_alerts",
    "wrapup_time": "daily_wrapup",
}
# Every key below has a real producer behind it today.
ENFORCED_KEYS = (
    "channels",
    "daily_briefing",
    "reminders",
    "learning_daily",
    "reading_daily",
    "diary_nudge",
    "habit_nudge",
    "money_alerts",
    "learning_time",
    "reading_time",
    "diary_time",
    "habit_time",
    "money_time",
    "daily_wrapup",
    "wrapup_time",
    "quiet_hours",
)


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise LifeError(f"{name} must be true or false.")
    return value


class NotificationService:
    def __init__(
        self,
        profiles: ProfileService,
        automations: AutomationStore,
        *,
        audit: AuditLog | None = None,
    ) -> None:
        self._profiles = profiles
        self._automations = automations
        self._audit = audit

    def policy(self, owner: str) -> NotificationPolicy:
        return NotificationPolicy.from_stored(self._profiles.get(owner).notification_prefs)

    def _by_kind(self, owner: str) -> dict[str, Automation]:
        self._automations.ensure_defaults(owner)
        return {a.kind: a for a in self._automations.list(owner)}

    def get(self, owner: str) -> dict[str, Any]:
        policy = self.policy(owner)
        autos = self._by_kind(owner)

        def enabled(kind: str) -> bool:
            row = autos.get(kind)
            return bool(row and row.enabled)

        def at(kind: str) -> str:
            row = autos.get(kind)
            return row.schedule_time if row else "08:00"

        return {
            "channels": {"in_app": policy.in_app, "telegram": policy.telegram},
            "daily_briefing": enabled("daily_briefing"),
            "reminders": policy.reminders,
            "learning_daily": enabled("learning_daily"),
            "reading_daily": enabled("reading_daily"),
            "diary_nudge": enabled("diary_nudge"),
            "habit_nudge": enabled("habit_nudge"),
            "money_alerts": enabled("money_alerts"),
            "daily_wrapup": enabled("daily_wrapup"),
            "learning_time": at("learning_daily"),
            "reading_time": at("reading_daily"),
            "diary_time": at("diary_nudge"),
            "habit_time": at("habit_nudge"),
            "money_time": at("money_alerts"),
            "wrapup_time": at("daily_wrapup") if "daily_wrapup" in autos else "21:00",
            "quiet_hours": {
                "enabled": policy.quiet_enabled,
                "start": policy.quiet_start,
                "end": policy.quiet_end,
            },
            "enforced": list(ENFORCED_KEYS),
        }

    def update(self, owner: str, patch: Mapping[str, Any]) -> dict[str, Any]:
        autos = self._by_kind(owner)
        profile = self._profiles.get(owner)
        stored: dict[str, Any] = dict(profile.notification_prefs or {})

        channels = dict(stored.get("channels") or {})
        if "channels" in patch:
            sent = patch["channels"]
            if not isinstance(sent, Mapping):
                raise LifeError("channels must be an object.")
            for key in ("in_app", "telegram"):
                if key in sent:
                    channels[key] = _bool(sent[key], f"channels.{key}")
        quiet = dict(stored.get("quiet_hours") or {})
        if "quiet_hours" in patch:
            sent_q = patch["quiet_hours"]
            if not isinstance(sent_q, Mapping):
                raise LifeError("quiet_hours must be an object.")
            if "enabled" in sent_q:
                quiet["enabled"] = _bool(sent_q["enabled"], "quiet_hours.enabled")
            for key in ("start", "end"):
                if key in sent_q:
                    quiet[key] = valid_hhmm(sent_q[key], f"quiet_hours.{key}")
        reminders = (
            _bool(patch["reminders"], "reminders")
            if "reminders" in patch
            else stored.get("reminders", True)
        )

        touched: list[Automation] = []
        for key, kind in _FLAG_KINDS.items():
            if key in patch and kind in autos:
                autos[kind].enabled = _bool(patch[key], key)
                touched.append(autos[kind])
        for key, kind in _TIME_KINDS.items():
            if key in patch and kind in autos:
                autos[kind].schedule_time = valid_hhmm(patch[key], key)
                touched.append(autos[kind])

        # Validation done: persist.
        stored.update({"channels": channels, "quiet_hours": quiet, "reminders": reminders})
        profile.notification_prefs = stored
        self._profiles.save(profile)
        for automation in {a.id: a for a in touched}.values():
            self._automations.save(automation)
        if self._audit is not None:
            self._audit.record("profile.notifications_updated", owner, {"keys": sorted(patch)})
        return self.get(owner)
