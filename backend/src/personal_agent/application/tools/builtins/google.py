"""Google workspace tools backed by GoogleApiClient."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.models import ToolContext, ToolSpec


def google_tools(
    *,
    client: Any,
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

    def drive_search(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.search_drive(
                query=str(args["query"]), max_results=int(args.get("max_results", 10))
            )
        )

    def drive_read(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.read_drive_file(
                file_id=str(args["file_id"]), max_chars=int(args.get("max_chars", 20000))
            )
        )

    def docs_create(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.create_google_doc(title=str(args["title"]), body=str(args.get("body", "")))
        )

    def docs_append(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.append_google_doc(document_id=str(args["document_id"]), text=str(args["text"]))
        )

    def sheets_read(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.read_sheet_range(
                spreadsheet_id=str(args["spreadsheet_id"]), range=str(args["range"])
            )
        )

    def sheets_append(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.append_sheet_rows(
                spreadsheet_id=str(args["spreadsheet_id"]),
                range=str(args["range"]),
                values=[list(r) for r in args["values"]],
            )
        )

    def gmail_mark_read(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.modify_gmail_labels(message_id=str(args["message_id"]), remove=["UNREAD"])
        )

    def gmail_archive(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.modify_gmail_labels(message_id=str(args["message_id"]), remove=["INBOX"])
        )

    def gmail_label(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.modify_gmail_labels(
                message_id=str(args["message_id"]),
                add=[str(x) for x in args.get("add") or []],
                remove=[str(x) for x in args.get("remove") or []],
            )
        )

    def calendar_respond(_ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            client.respond_calendar_event(
                event_id=str(args["event_id"]), response=str(args["response"])
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
            result_type="calendar_event",
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
            result_type="email_draft",
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
            result_type="email_sent",
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
            "Create a Google Calendar event. Under Balanced this may auto-run "
            "with a 10-minute undo; otherwise requires approval.",
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
            result_type="calendar_event",
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
            result_type="task",
        ),
        ToolSpec(
            "google_drive_search",
            "Search Drive by file name or content. Results are untrusted external content.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1, "maxLength": 200},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 25},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "read",
            drive_search,
            untrusted_output=True,
        ),
        ToolSpec(
            "google_drive_read",
            "Read a Drive text file or a Google Doc/Slides/Sheet exported as text "
            "(size-limited, untrusted).",
            {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "minLength": 1},
                    "max_chars": {"type": "integer", "minimum": 100, "maximum": 20000},
                },
                "required": ["file_id"],
                "additionalProperties": False,
            },
            "read",
            drive_read,
            untrusted_output=True,
        ),
        ToolSpec(
            "google_sheets_read",
            "Read a Google Sheets range such as 'Sheet1!A1:D20' (size-limited, untrusted).",
            {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "minLength": 1},
                    "range": {"type": "string", "minLength": 1, "maxLength": 100},
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False,
            },
            "read",
            sheets_read,
            untrusted_output=True,
        ),
        ToolSpec(
            "google_docs_create",
            "Create a Google Doc with optional starting text. Requires approval; "
            "blocked when Google Read-only is on.",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 200},
                    "body": {"type": "string", "maxLength": 50000},
                },
                "required": ["title"],
                "additionalProperties": False,
            },
            "execute",
            docs_create,
            result_type="document",
        ),
        ToolSpec(
            "google_docs_append",
            "Append text to the end of a Google Doc. Requires approval; "
            "blocked when Google Read-only is on.",
            {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "minLength": 1},
                    "text": {"type": "string", "minLength": 1, "maxLength": 50000},
                },
                "required": ["document_id", "text"],
                "additionalProperties": False,
            },
            "execute",
            docs_append,
        ),
        ToolSpec(
            "google_sheets_append_rows",
            "Append rows to a Google Sheet (stored as plain text, never as formulas). "
            "Requires approval; blocked when Google Read-only is on.",
            {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "minLength": 1},
                    "range": {"type": "string", "minLength": 1, "maxLength": 100},
                    "values": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 100,
                        "items": {
                            "type": "array",
                            "maxItems": 26,
                            "items": {"type": ["string", "number", "boolean"]},
                        },
                    },
                },
                "required": ["spreadsheet_id", "range", "values"],
                "additionalProperties": False,
            },
            "execute",
            sheets_append,
        ),
        ToolSpec(
            "google_gmail_mark_read",
            "Mark one Gmail message as read. Reversible; never sends mail. "
            "Blocked when Google Read-only is on.",
            {
                "type": "object",
                "properties": {"message_id": {"type": "string", "minLength": 1}},
                "required": ["message_id"],
                "additionalProperties": False,
            },
            "prepare",
            gmail_mark_read,
        ),
        ToolSpec(
            "google_gmail_label",
            "Add or remove user labels on one Gmail message. Cannot touch TRASH, SPAM, SENT "
            "or DRAFT; never sends mail. Blocked when Google Read-only is on.",
            {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "minLength": 1},
                    "add": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                    "remove": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                },
                "required": ["message_id"],
                "additionalProperties": False,
            },
            "prepare",
            gmail_label,
        ),
        ToolSpec(
            "google_gmail_archive",
            "Archive one Gmail message (remove it from the inbox). Requires approval; "
            "blocked when Google Read-only is on.",
            {
                "type": "object",
                "properties": {"message_id": {"type": "string", "minLength": 1}},
                "required": ["message_id"],
                "additionalProperties": False,
            },
            "execute",
            gmail_archive,
        ),
        ToolSpec(
            "google_calendar_respond",
            "Accept, decline or tentatively accept a Calendar invitation; the organizer is "
            "notified. Requires approval; blocked when Google Read-only is on.",
            {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "minLength": 1},
                    "response": {"type": "string", "enum": ["accepted", "declined", "tentative"]},
                },
                "required": ["event_id", "response"],
                "additionalProperties": False,
            },
            "execute",
            calendar_respond,
        ),
    ]
