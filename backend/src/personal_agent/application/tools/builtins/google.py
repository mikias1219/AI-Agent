"""Google workspace tools backed by GoogleApiClient."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from personal_agent.domain.models import ToolContext, ToolSpec
from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient


def google_tools(*, client: GoogleApiClient) -> list[ToolSpec]:
    def gmail_list(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        page = int(args.get("page", 1))
        page_size = int(args.get("page_size", 10))
        return json.dumps(client.list_gmail(page=page, page_size=page_size))

    def calendar_list(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        page = int(args.get("page", 1))
        page_size = int(args.get("page_size", 10))
        return json.dumps(client.list_calendar(page=page, page_size=page_size))

    def drive_list(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        page = int(args.get("page", 1))
        page_size = int(args.get("page_size", 10))
        return json.dumps(client.list_drive(page=page, page_size=page_size))

    def gmail_send(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.send_gmail(to=args["to"], subject=args["subject"], body=args["body"])
        )

    def calendar_create(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.create_calendar_event(
                title=args["title"],
                starts_at=args["starts_at"],
                ends_at=args["ends_at"],
                location=args.get("location", ""),
            )
        )

    def calendar_update(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.update_calendar_event(
                event_id=args["event_id"],
                title=args.get("title"),
                starts_at=args.get("starts_at"),
                ends_at=args.get("ends_at"),
                location=args.get("location"),
            )
        )

    page_schema = {
        "type": "object",
        "properties": {
            "page": {"type": "integer", "minimum": 1},
            "page_size": {"type": "integer", "minimum": 1, "maximum": 50},
        },
        "additionalProperties": False,
    }

    return [
        ToolSpec(
            "google_gmail_list",
            "List recent Gmail inbox messages for the connected Google account.",
            page_schema,
            "read",
            gmail_list,
            untrusted_output=True,  # external content (BR-04)
        ),
        ToolSpec(
            "google_calendar_list",
            "List upcoming calendar events on the connected Google account.",
            page_schema,
            "read",
            calendar_list,
            untrusted_output=True,  # external content (BR-04)
        ),
        ToolSpec(
            "google_drive_list",
            "List recently modified Drive files for the connected Google account.",
            page_schema,
            "read",
            drive_list,
            untrusted_output=True,  # external content (BR-04)
        ),
        ToolSpec(
            "google_gmail_send",
            "Send an email via Gmail. Requires human approval before sending.",
            {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "minLength": 1},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
                "additionalProperties": False,
            },
            "execute",
            gmail_send,
        ),
        ToolSpec(
            "google_calendar_create",
            "Create a Google Calendar event. Requires human approval.",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "starts_at": {"type": "string", "minLength": 1},
                    "ends_at": {"type": "string", "minLength": 1},
                    "location": {"type": "string"},
                },
                "required": ["title", "starts_at", "ends_at"],
                "additionalProperties": False,
            },
            "execute",
            calendar_create,
        ),
        ToolSpec(
            "google_calendar_update",
            "Update an existing Google Calendar event. Requires human approval.",
            {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "minLength": 1},
                    "title": {"type": "string"},
                    "starts_at": {"type": "string"},
                    "ends_at": {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["event_id"],
                "additionalProperties": False,
            },
            "execute",
            calendar_update,
        ),
    ]
