"""Suggestion tools. Proposals only — accepting still goes through the registry gate."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from personal_agent.application.services.suggestion_service import SuggestionService
from personal_agent.domain.exceptions import ToolInputError
from personal_agent.domain.models import ToolContext, ToolSpec
from personal_agent.domain.suggestions import SuggestionError

# Soft ceiling so Needs you stays calm (open suggestions, not all-time).
DEFAULT_DAILY_SUGGESTION_CAP = 5


def suggestion_tools(
    suggestions: SuggestionService,
    *,
    daily_cap: int = DEFAULT_DAILY_SUGGESTION_CAP,
) -> list[ToolSpec]:
    def propose(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        owner = ctx.user_id or "dashboard"
        open_count = len(suggestions.open(owner))
        if open_count >= daily_cap:
            raise ToolInputError(
                f"Suggestion cap ({daily_cap} open) reached. Wait for the owner to clear Needs you."
            )
        action = None
        tool_name = str(args.get("tool_name") or "").strip()
        if tool_name:
            action = {
                "tool_name": tool_name,
                "arguments": dict(args.get("arguments") or {}),
            }
        expires_hours = args.get("expires_in_hours")
        expires_in = (
            timedelta(hours=float(expires_hours))
            if expires_hours is not None
            else timedelta(days=2)
        )
        try:
            suggestion = suggestions.create(
                owner,
                kind=str(args["kind"]),
                title=str(args["title"]),
                reason=str(args["reason"]),
                source=str(args["source"]),
                proposed_action=action,
                expires_in=expires_in,
                origin=ctx.origin or "agent",
            )
        except SuggestionError as exc:
            raise ToolInputError(str(exc)) from exc
        return json.dumps(
            {
                "id": suggestion.id,
                "kind": suggestion.kind,
                "title": suggestion.title,
                "result_type": "suggestion",
                "summary": f"Suggested: {suggestion.title}",
            }
        )

    return [
        ToolSpec(
            name="suggestion_propose",
            description=(
                "Propose something for Needs you. Always cite the source (what data you read). "
                "Optional tool_name/arguments become the action if the owner accepts; "
                "execute and destructive tools still need a separate approval. "
                "Use sparingly — a few clear proposals beat many."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 32,
                        "description": "e.g. followup, mail_reply, deadline, idea",
                    },
                    "title": {"type": "string", "minLength": 1, "maxLength": 256},
                    "reason": {"type": "string", "minLength": 1, "maxLength": 1000},
                    "source": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 256,
                        "description": "Citation: where the idea came from",
                    },
                    "tool_name": {"type": "string", "maxLength": 128},
                    "arguments": {"type": "object"},
                    "expires_in_hours": {"type": "number", "minimum": 1, "maximum": 168},
                },
                "required": ["kind", "title", "reason", "source"],
                "additionalProperties": False,
            },
            access_kind="prepare",
            handler=propose,
            result_type="suggestion",
        )
    ]


__all__ = ["DEFAULT_DAILY_SUGGESTION_CAP", "suggestion_tools"]
