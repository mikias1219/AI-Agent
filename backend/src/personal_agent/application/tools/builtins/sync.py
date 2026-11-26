"""Drive backup and Calendar sync tools (contract sections 8-9).

Both writing tools are `execute` class: they go through the registry's approval gate. The
argument list is the snapshot the owner approved, so what runs is exactly what was shown.
Neither tool deletes anything. Content of notes is data only: it is rendered into Markdown
and uploaded, never interpreted.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from personal_agent.application.services.calendar_sync_service import (
    MAX_BATCH as CALENDAR_BATCH,
)
from personal_agent.application.services.calendar_sync_service import CalendarSyncService
from personal_agent.application.services.drive_sync_service import DriveSyncService
from personal_agent.domain.drive_sync import MAX_BATCH, OBJECT_TYPES
from personal_agent.domain.models import ToolContext, ToolSpec


def drive_tools(service: DriveSyncService) -> list[ToolSpec]:
    def push(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(service.execute_push(ctx.user_id, list(args["items"])))

    def status(ctx: ToolContext, _args: Mapping[str, Any]) -> str:
        data = service.status(ctx.user_id)
        pending = data["pending"]
        count = (
            pending["notes"]
            + pending["diary"]
            + pending["daily"]
            + pending["files"]
            + int(pending["learning"])
            + int(pending["reading"])
        )
        connected = "connected" if data["connected"] else "not connected"
        return json.dumps(
            {
                "result_type": "drive_status",
                "summary": f"Drive is {connected}; {count} object(s) waiting for backup.",
                **data,
            }
        )

    return [
        ToolSpec(
            "drive_sync_push",
            "Back up the listed notes, diary entries, daily summaries, files, vocabulary and "
            "reading log to the Compass folder in Google Drive. Overwrites Compass's own copies, "
            "never deletes anything in Drive. The owner approves the exact list.",
            {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_BATCH,
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": list(OBJECT_TYPES)},
                                "id": {"type": "string", "minLength": 1, "maxLength": 64},
                                "title": {"type": "string", "maxLength": 120},
                            },
                            "required": ["type", "id"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["items"],
                "additionalProperties": False,
            },
            "execute",
            push,
            result_type="drive_sync",
            integration="google",
        ),
        ToolSpec(
            "drive_sync_status",
            "Say whether Drive backup is connected and how many objects are waiting.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            "read",
            status,
            result_type="drive_status",
            integration="google",
        ),
    ]


def calendar_sync_tools(service: CalendarSyncService) -> list[ToolSpec]:
    def sync(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            service.execute(
                ctx.user_id, list(args["task_ids"]), all_day=bool(args.get("all_day", False))
            )
        )

    return [
        ToolSpec(
            "task_calendar_sync",
            "Create or update Google Calendar events for the listed tasks that have a due time "
            "(date-only tasks only with all_day). Completed tasks get an outcome prefix. "
            "Requires approval of the exact list; never deletes events.",
            {
                "type": "object",
                "properties": {
                    "task_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": CALENDAR_BATCH,
                        "items": {"type": "string", "minLength": 1, "maxLength": 64},
                    },
                    "titles": {
                        "type": "array",
                        "maxItems": CALENDAR_BATCH,
                        "items": {"type": "string", "maxLength": 120},
                    },
                    "all_day": {"type": "boolean"},
                },
                "required": ["task_ids"],
                "additionalProperties": False,
            },
            "execute",
            sync,
            result_type="calendar_sync",
            integration="google",
        )
    ]
