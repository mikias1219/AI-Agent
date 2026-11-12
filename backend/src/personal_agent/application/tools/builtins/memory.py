"""Memory tools: propose save, search, forget (MEM-01, MEM-02)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from personal_agent.application.run_events import emit_event
from personal_agent.application.services.memory_service import MemoryService
from personal_agent.domain.exceptions import PermissionDeniedError, StorageError
from personal_agent.domain.models import ToolContext, ToolSpec


def memory_tools(memories: MemoryService) -> list[ToolSpec]:
    def save(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        proposal = memories.propose(str(args.get("kind", "fact")), str(args.get("content", "")))
        payload = {
            **proposal,
            "action": "save",
            "source_run_id": ctx.run_id,
        }
        emit_event(
            ctx,
            "memory.proposed",
            kind=proposal["kind"],
            content=proposal["content"],
            run_id=ctx.run_id,
        )
        return json.dumps(payload)

    def search(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        query = str(args.get("query", "")).strip()
        found = memories.search(ctx.user_id, query, limit=8)
        emit_event(
            ctx,
            "memory.used",
            ids=[m.id for m in found],
            items=[{"id": m.id, "kind": m.kind, "content": m.content} for m in found],
        )
        return json.dumps(
            [{"id": m.id, "kind": m.kind, "content": m.content} for m in found],
            ensure_ascii=False,
        )

    def forget(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        memory_id = str(args.get("memory_id", "")).strip()
        if not memory_id:
            raise StorageError("memory_id is required.")
        try:
            memories.delete(memory_id, ctx.user_id)
        except StorageError as exc:
            raise PermissionDeniedError(str(exc)) from exc
        return json.dumps({"id": memory_id, "status": "deleted"})

    def forget_all(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        from personal_agent.application.services.memory_service import FORGET_CONFIRM_PHRASE

        phrase = str(args.get("confirm_phrase", "")).strip()
        issued = memories.issue_forget_token(ctx.user_id)
        count = memories.forget_all(
            ctx.user_id,
            token=issued["token"],
            confirm_phrase=phrase or FORGET_CONFIRM_PHRASE,
        )
        return json.dumps({"deleted": count, "status": "wiped"})

    return [
        ToolSpec(
            name="memory_save",
            description=(
                "Propose saving a personal memory (preference, fact, person, or routine). "
                "Does not write until the owner confirms the Save chip."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["preference", "fact", "person", "routine"],
                    },
                    "content": {"type": "string", "minLength": 1, "maxLength": 2000},
                },
                "required": ["kind", "content"],
                "additionalProperties": False,
            },
            access_kind="prepare",
            handler=save,
            result_type="memory_proposal",
        ),
        ToolSpec(
            name="memory_search",
            description=(
                "Search the owner's memories by meaning or keywords. Returns up to 8 items."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1, "maxLength": 500},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            access_kind="read",
            handler=search,
            result_type="generic",
        ),
        ToolSpec(
            name="memory_forget",
            description="Permanently remove one memory by id after the owner asked to forget it.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "minLength": 8, "maxLength": 64},
                },
                "required": ["memory_id"],
                "additionalProperties": False,
            },
            access_kind="execute",
            handler=forget,
            result_type="generic",
        ),
        ToolSpec(
            name="memory_forget_all",
            description=(
                "Permanently delete every memory for the owner. Destructive; requires approval "
                "and confirm_phrase 'forget everything'."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "confirm_phrase": {"type": "string", "minLength": 1},
                },
                "required": ["confirm_phrase"],
                "additionalProperties": False,
            },
            access_kind="destructive",
            handler=forget_all,
            result_type="generic",
        ),
    ]


__all__ = ["memory_tools"]
