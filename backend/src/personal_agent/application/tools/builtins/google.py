"""Google workspace tools backed by GoogleApiClient."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.models import ToolContext, ToolSpec
from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient


def google_tools(
    *,
    client: GoogleApiClient,
    tasks: TaskService | None = None,
) -> list[ToolSpec]:
    def gmail_list(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        page = int(args.get("page", 1))
        page_size = int(args.get("page_size", 10))
        return json.dumps(client.list_gmail(page=page, page_size=page_size))

    def gmail_search(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.search_gmail(
                query=str(args["query"]),
                max_results=int(args.get("max_results", 10)),
            )
        )

    def gmail_read(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(client.read_gmail(message_id=str(args["message_id"])))

    def calendar_list(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        page = int(args.get("page", 1))
        page_size = int(args.get("page_size", 10))
        return json.dumps(client.list_calendar(page=page, page_size=page_size))

    def calendar_find_free_slots(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.find_free_slots(
                time_min=str(args["time_min"]),
                time_max=str(args["time_max"]),
                duration_minutes=int(args.get("duration_minutes", 30)),
            )
        )

    def drive_list(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        page = int(args.get("page", 1))
        page_size = int(args.get("page_size", 10))
        return json.dumps(client.list_drive(page=page, page_size=page_size))

    def gmail_create_draft(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.create_gmail_draft(
                to=str(args["to"]),
                subject=str(args["subject"]),
                body=str(args["body"]),
                thread_id=str(args["thread_id"]) if args.get("thread_id") else None,
            )
        )

    def gmail_send(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.send_gmail(to=args["to"], subject=args["subject"], body=args["body"])
        )

    def gmail_reply(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.reply_gmail(
                message_id=str(args["message_id"]),
                body=str(args["body"]),
                to=str(args["to"]) if args.get("to") else None,
                subject=str(args["subject"]) if args.get("subject") else None,
            )
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

    def calendar_delete(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(client.delete_calendar_event(event_id=str(args["event_id"])))

    def create_task_from_email(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        if tasks is None:
            return json.dumps({"error": "Task service unavailable."})
        message = client.read_gmail(message_id=str(args["message_id"]))
        title = str(args.get("title") or message.get("subject") or "Email follow-up").strip()
        description = (
            f"From email {message.get('id')}\n"
            f"From: {message.get('from', '')}\n"
            f"Subject: {message.get('subject', '')}\n\n"
            f"{message.get('body', '')}"
        )
        task_id = tasks.create(
            title,
            description[:4000],
            ctx.user_id,
            source="agent",
            tags=["from-email"],
        )
        return json.dumps(
            {
                "task_id": task_id,
                "title": title,
                "message_id": message.get("id"),
                "untrusted_source": True,
            }
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
            untrusted_output=True,
        ),
        ToolSpec(
            "google_gmail_search",
            "Search Gmail with a query string. Results are untrusted external content.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 25},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "read",
            gmail_search,
            untrusted_output=True,
        ),
        ToolSpec(
            "google_gmail_read",
            "Read one Gmail message as sanitized plain text (size-limited, untrusted).",
            {
                "type": "object",
                "properties": {"message_id": {"type": "string", "minLength": 1}},
                "required": ["message_id"],
                "additionalProperties": False,
            },
            "read",
            gmail_read,
            untrusted_output=True,
        ),
        ToolSpec(
            "google_calendar_list",
            "List upcoming calendar events on the connected Google account.",
            page_schema,
            "read",
            calendar_list,
            untrusted_output=True,
        ),
        ToolSpec(
            "google_calendar_find_free_slots",
            "Find free calendar slots between time_min and time_max (RFC3339).",
            {
                "type": "object",
                "properties": {
                    "time_min": {"type": "string", "minLength": 1},
                    "time_max": {"type": "string", "minLength": 1},
                    "duration_minutes": {"type": "integer", "minimum": 5, "maximum": 480},
                },
                "required": ["time_min", "time_max"],
                "additionalProperties": False,
            },
            "read",
            calendar_find_free_slots,
        ),
        ToolSpec(
            "google_drive_list",
            "List recently modified Drive files for the connected Google account.",
            page_schema,
            "read",
            drive_list,
            untrusted_output=True,
        ),
        ToolSpec(
            "google_gmail_create_draft",
            "Create a Gmail draft without sending. Blocked when Google Read-only is on.",
            {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "minLength": 1},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "thread_id": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
                "additionalProperties": False,
            },
            "prepare",
            gmail_create_draft,
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
            "google_gmail_reply",
            "Reply to an existing Gmail message. Requires human approval.",
            {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "minLength": 1},
                    "body": {"type": "string", "minLength": 1},
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                },
                "required": ["message_id", "body"],
                "additionalProperties": False,
            },
            "execute",
            gmail_reply,
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
        ToolSpec(
            "google_calendar_delete_event",
            "Delete a Google Calendar event. Destructive; requires human approval.",
            {
                "type": "object",
                "properties": {"event_id": {"type": "string", "minLength": 1}},
                "required": ["event_id"],
                "additionalProperties": False,
            },
            "destructive",
            calendar_delete,
        ),
        ToolSpec(
            "google_create_task_from_email",
            "Create a task from a Gmail message (subject/body as fields). Does not send mail.",
            {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "minLength": 1},
                    "title": {"type": "string"},
                },
                "required": ["message_id"],
                "additionalProperties": False,
            },
            "prepare",
            create_task_from_email,
            untrusted_output=True,
        ),
    ]
