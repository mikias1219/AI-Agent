"""Task tools use the same application service as the dashboard and CLI."""

import json
from collections.abc import Mapping
from typing import Any

from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.exceptions import PermissionDeniedError
from personal_agent.domain.models import TaskStatus, ToolContext, ToolSpec


def task_tools(tasks: TaskService) -> list[ToolSpec]:
    def create(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        task_id = tasks.create(args["title"], args.get("description", ""), ctx.user_id)
        return json.dumps({"id": task_id, "title": tasks.get(task_id).title, "status": "planned"})

    def list_tasks(ctx: ToolContext, _args: Mapping[str, Any]) -> str:
        return json.dumps(
            [
                {"id": t.id, "title": t.title, "status": t.status.value}
                for t in tasks.list()
                if t.owner_user_id == ctx.user_id
            ]
        )

    def update(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        task = tasks.get(args["task_id"])
        if task is None or task.owner_user_id != ctx.user_id:
            raise PermissionDeniedError("Task is unavailable in this conversation’s user context.")
        tasks.advance(task.id, TaskStatus(args["status"]))
        return json.dumps({"id": task.id, "status": args["status"]})

    return [
        ToolSpec(
            "task_create",
            "Create a personal task when the user requests it.",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 256},
                    "description": {"type": "string"},
                },
                "required": ["title"],
                "additionalProperties": False,
            },
            "prepare",
            create,
        ),
        ToolSpec(
            "task_list",
            "List tasks belonging to the current user.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            "read",
            list_tasks,
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
            update,
        ),
    ]
