"""Task tools use the same application service as the dashboard and CLI."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from personal_agent.application.services.day_service import DayService, parse_day
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.dates import parse_due
from personal_agent.domain.days import day_line, effective_outcome
from personal_agent.domain.exceptions import PermissionDeniedError, ToolInputError
from personal_agent.domain.models import Task, TaskPriority, TaskStatus, ToolContext, ToolSpec
from personal_agent.domain.task_rules import OPEN_STATUSES, OUTCOMES, TaskView

if TYPE_CHECKING:
    from personal_agent.application.services.scheduler_service import SchedulerService

_UNAVAILABLE = "Task is unavailable in this conversation’s user context."
_PRIORITIES = [p.value for p in TaskPriority]
_TAGS = {"type": "array", "items": {"type": "string", "maxLength": 64}, "maxItems": 20}
_DUE_HELP = "Due date: ISO 8601 or plain words like 'friday 3pm', 'tomorrow', 'in 2 days'."


def task_summary(task: Task) -> dict[str, Any]:
    """Compact, model-visible task dict (ISO datetimes; empty fields omitted by value)."""
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "priority": task.priority.value,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "project": task.project,
        "tags": list(task.tags),
        "plan_date": task.plan_date.isoformat() if task.plan_date else None,
        "target_value": task.target_value,
        "target_unit": task.target_unit,
        "actual_value": task.actual_value,
        "outcome": effective_outcome(task),
    }


def task_tools(
    tasks: TaskService,
    profiles: ProfileService | None = None,
    scheduler: SchedulerService | None = None,
    days: DayService | None = None,
) -> list[ToolSpec]:
    def timezone_of(ctx: ToolContext) -> str:
        return profiles.timezone_for(ctx.user_id) if profiles is not None else "UTC"

    def owned(ctx: ToolContext, task_id: str) -> Task:
        task = tasks.get(task_id)
        if task is None or task.owner_user_id != ctx.user_id:
            raise PermissionDeniedError(_UNAVAILABLE)
        return task

    def create(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        due_at = parse_due(args["due"], timezone_of(ctx)) if args.get("due") else None
        task_id = tasks.create(
            args["title"],
            args.get("description", ""),
            ctx.user_id,
            priority=TaskPriority(args.get("priority", "none")),
            due_at=due_at,
            project=args.get("project", ""),
            tags=args.get("tags"),
            source="agent",
            plan_date=parse_day(args["plan_date"], "plan_date") if args.get("plan_date") else None,
            target_value=args.get("target_value"),
            target_unit=args.get("target_unit", ""),
            timezone=timezone_of(ctx),
        )
        created = tasks.get(task_id)
        if created is None:
            return json.dumps({"id": task_id, "title": str(args["title"]).strip()})
        return json.dumps(task_summary(created))

    def list_tasks(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        view = TaskView(args["view"]) if args.get("view") else None
        status = TaskStatus(args["status"]) if args.get("status") else None
        found = tasks.list(
            status,
            view=view,
            owner_user_id=ctx.user_id,
            timezone=timezone_of(ctx),
        )
        if args.get("project"):
            found = [t for t in found if t.project.lower() == str(args["project"]).lower()]
        if args.get("priority"):
            found = [t for t in found if t.priority.value == args["priority"]]
        return json.dumps([task_summary(t) for t in found])

    def search(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        found = tasks.search(args["query"], owner_user_id=ctx.user_id)
        return json.dumps([task_summary(t) for t in found])

    def update(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        task = owned(ctx, args["task_id"])
        fields: dict[str, Any] = {}
        for key in ("title", "description", "project", "tags"):
            if key in args:
                fields[key] = args[key]
        if "priority" in args:
            fields["priority"] = TaskPriority(args["priority"])
        if "due" in args:  # null or empty string clears the due date
            due = args["due"]
            fields["due_at"] = parse_due(due, timezone_of(ctx)) if due else None
        updated = tasks.update(task.id, **fields) if fields else task
        payload = task_summary(updated)
        if "remind_at" in args:
            if scheduler is None:
                raise ToolInputError("Reminders are not available.")
            when = args["remind_at"]
            if not when:
                raise ToolInputError("remind_at must be a date/time or relative phrase.")
            remind_at = parse_due(str(when), timezone_of(ctx))
            if remind_at is None:
                raise ToolInputError("Could not parse remind_at.")
            reminder = scheduler.create_reminder(
                text=f"Task: {updated.title}",
                remind_at=remind_at,
                owner_user_id=ctx.user_id,
                task_id=updated.id,
            )
            payload["reminder"] = {
                "id": reminder.id,
                "remind_at": reminder.remind_at.isoformat(),
            }
        return json.dumps(payload)

    def update_status(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        task = owned(ctx, args["task_id"])
        tasks.advance(task.id, TaskStatus(args["status"]))
        return json.dumps({"id": task.id, "status": args["status"]})

    def reopen(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        task = owned(ctx, args["task_id"])
        return json.dumps(task_summary(tasks.reopen(task.id)))

    def delete(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        task = owned(ctx, args["task_id"])
        tasks.soft_delete(task.id)
        return json.dumps({"id": task.id, "deleted": True})

    def complete(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        """Record an achievement. Ambiguous or missing matches change nothing."""
        if args.get("task_id"):
            task = owned(ctx, str(args["task_id"]))
        else:
            query = str(args.get("title_query") or "").strip()
            if not query:
                raise ToolInputError("Give task_id or title_query.")
            today = tasks.today_for(ctx.user_id, timezone_of(ctx))
            candidates = [
                t
                for t in tasks.tasks_on(ctx.user_id, today)
                if t.status in OPEN_STATUSES and query.casefold() in t.title.casefold()
            ]
            if len(candidates) != 1:
                reason = "no_match" if not candidates else "ambiguous"
                text = (
                    "No open task of today matches. Nothing was changed."
                    if not candidates
                    else "Several open tasks match. Nothing was changed; ask which one."
                )
                return json.dumps(
                    {
                        "result_type": "task_candidates",
                        "completed": False,
                        "reason": reason,
                        "summary": text,
                        "candidates": [task_summary(t) for t in candidates],
                    }
                )
            task = candidates[0]
        done = tasks.complete(
            task.id,
            outcome=args.get("outcome"),
            actual_value=args.get("actual_value"),
            note=args.get("note"),
        )
        payload = task_summary(done)
        payload["completed"] = True
        payload["summary"] = f"{done.title}: {payload['outcome']}"
        return json.dumps(payload)

    def _days() -> DayService:
        if days is None:
            raise ToolInputError("Days are not available.")
        return days

    def day_summary(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        service = _days()
        day = parse_day(args["date"], "date") if args.get("date") else service.today(ctx.user_id)
        found = service.tasks_of(ctx.user_id, day)
        counts = service.summary_of(ctx.user_id, day)
        text = (
            f"{day.isoformat()}: {day_line(counts)}."
            if counts.planned
            else (f"{day.isoformat()}: no tasks planned.")
        )
        return json.dumps(
            {
                "result_type": "day_summary",
                "date": day.isoformat(),
                "summary": text,
                "counts": counts.to_dict(),
                "tasks": [task_summary(t) for t in found],
            }
        )

    def day_carry_over(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        service = _days()
        day = parse_day(args["date"], "date") if args.get("date") else service.today(ctx.user_id)
        target = parse_day(args["to"], "to") if args.get("to") else None
        moved = service.carry_over(ctx.user_id, day, target)
        return json.dumps(
            {
                "result_type": "day_carry_over",
                "summary": f"Moved {moved['moved']} unfinished task(s) to {moved['to']}.",
                **moved,
            }
        )

    task_id_schema = {
        "type": "object",
        "properties": {"task_id": {"type": "string"}},
        "required": ["task_id"],
        "additionalProperties": False,
    }
    return [
        ToolSpec(
            "task_create",
            "Create a personal task when the user requests it. Set due, priority, "
            "project and tags when the user states them.",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 256},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": _PRIORITIES},
                    "due": {"type": "string", "description": _DUE_HELP},
                    "project": {"type": "string", "maxLength": 128},
                    "tags": _TAGS,
                    "target_value": {"type": "number", "exclusiveMinimum": 0},
                    "target_unit": {"type": "string", "maxLength": 20},
                    "plan_date": {
                        "type": "string",
                        "description": "Day of the task, YYYY-MM-DD (default: due date or today).",
                    },
                },
                "required": ["title"],
                "additionalProperties": False,
            },
            "prepare",
            create,
            result_type="task",
        ),
        ToolSpec(
            "task_list",
            "List tasks belonging to the current user. Optionally filter by view "
            "(today, upcoming, overdue), status, priority or project.",
            {
                "type": "object",
                "properties": {
                    "view": {"type": "string", "enum": [v.value for v in TaskView]},
                    "status": {"type": "string", "enum": [s.value for s in TaskStatus]},
                    "priority": {"type": "string", "enum": _PRIORITIES},
                    "project": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "read",
            list_tasks,
        ),
        ToolSpec(
            "task_search",
            "Search the current user's tasks by words in title, notes, project or tags.",
            {
                "type": "object",
                "properties": {"query": {"type": "string", "minLength": 1}},
                "required": ["query"],
                "additionalProperties": False,
            },
            "read",
            search,
        ),
        ToolSpec(
            "task_update",
            "Edit a task's title, notes, priority, due date, project or tags. Use task_list "
            "or task_search to get its exact ID. Pass due as an empty string to clear it.",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "title": {"type": "string", "minLength": 1, "maxLength": 256},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": _PRIORITIES},
                    "due": {"type": "string", "description": _DUE_HELP},
                    "remind_at": {
                        "type": "string",
                        "description": "Schedule a reminder for this task (ISO or relative).",
                    },
                    "project": {"type": "string", "maxLength": 128},
                    "tags": _TAGS,
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
            "prepare",
            update,
            result_type="task",
        ),
        ToolSpec(
            "task_update_status",
            "Update a task owned by the current user. Use task_list to get its exact ID.",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string", "enum": [s.value for s in TaskStatus]},
                },
                "required": ["task_id", "status"],
                "additionalProperties": False,
            },
            "prepare",
            update_status,
        ),
        ToolSpec(
            "task_reopen",
            "Reopen a done or cancelled task, returning it to planned.",
            task_id_schema,
            "prepare",
            reopen,
        ),
        ToolSpec(
            "task_complete",
            "Record that the owner did a task, e.g. 'I did 30 push-ups'. Give task_id, or "
            "title_query to match one open task of today by words in its title. If zero or "
            "several tasks match nothing is changed and the candidates are returned. Optional "
            "outcome (achieved, partial, missed, skipped), actual_value and a short note.",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "title_query": {"type": "string", "minLength": 1, "maxLength": 128},
                    "outcome": {"type": "string", "enum": list(OUTCOMES)},
                    "actual_value": {"type": "number", "minimum": 0},
                    "note": {"type": "string", "maxLength": 500},
                },
                "additionalProperties": False,
            },
            "prepare",
            complete,
            result_type="task",
        ),
        ToolSpec(
            "day_summary",
            "How a day went: counts (planned, achieved, partial, missed, skipped, open), the "
            "score and the task lines. Defaults to today; pass date as YYYY-MM-DD.",
            {
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "additionalProperties": False,
            },
            "read",
            day_summary,
            result_type="day_summary",
        ),
        ToolSpec(
            "day_carry_over",
            "Move a day's unfinished tasks (planned, in progress, blocked) to another day "
            "(default: tomorrow). Never touches done or cancelled tasks.",
            {
                "type": "object",
                "properties": {"date": {"type": "string"}, "to": {"type": "string"}},
                "additionalProperties": False,
            },
            "prepare",
            day_carry_over,
            result_type="day_carry_over",
        ),
        ToolSpec(
            "task_delete",
            "Delete a task (hidden from lists; requires human approval).",
            task_id_schema,
            "destructive",
            delete,
        ),
    ]
