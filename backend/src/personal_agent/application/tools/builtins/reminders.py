"""Reminder tools backed by SchedulerService (AUT-01, AG-TLS-01)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.scheduler_service import SchedulerService
from personal_agent.domain.dates import get_zone, parse_due
from personal_agent.domain.exceptions import PermissionDeniedError, ToolInputError
from personal_agent.domain.models import ToolContext, ToolSpec
from personal_agent.domain.scheduler import Reminder, ReminderStatus


def _reminder_payload(reminder: Reminder) -> dict[str, Any]:
    return {
        "id": reminder.id,
        "text": reminder.text,
        "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
        "task_id": reminder.task_id,
        "channels": list(reminder.channels),
        "status": reminder.status.value,
        "late": reminder.late,
    }


def reminder_tools(
    scheduler: SchedulerService,
    profiles: ProfileService | None = None,
) -> list[ToolSpec]:
    def timezone_of(ctx: ToolContext) -> str:
        return profiles.timezone_for(ctx.user_id) if profiles is not None else "UTC"

    def resolve_when(ctx: ToolContext, args: Mapping[str, Any]) -> datetime:
        if args.get("remind_at"):
            parsed = parse_due(str(args["remind_at"]), timezone_of(ctx))
            if parsed is None:
                raise ToolInputError("Could not parse remind_at.")
            return parsed
        if args.get("in_minutes") is not None:
            minutes = int(args["in_minutes"])
            if minutes < 1:
                raise ToolInputError("in_minutes must be at least 1.")
            zone = get_zone(timezone_of(ctx))
            return datetime.now(UTC).astimezone(zone) + timedelta(minutes=minutes)
        raise ToolInputError("Provide remind_at or in_minutes.")

    def create(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        text = str(args.get("text", "")).strip()
        if not text:
            raise ToolInputError("Reminder text is required.")
        channels = args.get("channels")
        if channels is not None and not isinstance(channels, list):
            raise ToolInputError("channels must be a list of strings.")
        reminder = scheduler.create_reminder(
            text=text,
            remind_at=resolve_when(ctx, args),
            owner_user_id=ctx.user_id,
            channels=[str(c) for c in channels] if channels else None,
            task_id=str(args["task_id"]) if args.get("task_id") else None,
        )
        return json.dumps(_reminder_payload(reminder))

    def list_reminders(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        status = None
        if args.get("status"):
            status = ReminderStatus(str(args["status"]))
        rows = scheduler.list_reminders(ctx.user_id, status=status)
        return json.dumps([_reminder_payload(r) for r in rows])

    def cancel(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        reminder_id = str(args.get("reminder_id", "")).strip()
        if not reminder_id:
            raise ToolInputError("reminder_id is required.")
        cancelled = scheduler.cancel_reminder(reminder_id, ctx.user_id)
        if cancelled is None:
            raise PermissionDeniedError("Reminder is unavailable in this conversation.")
        return json.dumps(_reminder_payload(cancelled))

    return [
        ToolSpec(
            name="reminder_create",
            description=(
                "Schedule a reminder for the owner. Pass remind_at (ISO or relative words) "
                "or in_minutes. Optional channels: inbox, telegram."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "minLength": 1, "maxLength": 500},
                    "remind_at": {"type": "string"},
                    "in_minutes": {"type": "integer", "minimum": 1, "maximum": 10080},
                    "channels": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["inbox", "telegram"]},
                        "maxItems": 2,
                    },
                    "task_id": {"type": "string"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            access_kind="prepare",
            handler=create,
            result_type="reminder",
        ),
        ToolSpec(
            name="reminder_list",
            description="List the owner's reminders, optionally filtered by status.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [s.value for s in ReminderStatus],
                    },
                },
                "additionalProperties": False,
            },
            access_kind="read",
            handler=list_reminders,
            result_type="reminder",
        ),
        ToolSpec(
            name="reminder_cancel",
            description="Cancel a scheduled reminder by id. Requires approval.",
            parameters_schema={
                "type": "object",
                "properties": {"reminder_id": {"type": "string", "minLength": 1}},
                "required": ["reminder_id"],
                "additionalProperties": False,
            },
            access_kind="execute",
            handler=cancel,
            result_type="reminder",
        ),
    ]


__all__ = ["reminder_tools"]
