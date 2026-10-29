"""Declarative helpers for defining tools.

A tool states its JSON-schema parameters, its `access_kind` (read | prepare |
execute) and a plain handler `fn(ctx, args) -> str`. The registry — not the
handler, and never the model — decides whether a call may run and whether it
needs human approval first.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from personal_agent.core.types import AccessKind, ToolContext, ToolSpec

SchemaArg = Mapping[str, Any]

Handler = Callable[[ToolContext, Mapping[str, Any]], str]


def tool(
    name: str,
    description: str,
    *,
    access_kind: AccessKind,
    schema: SchemaArg | None = None,
) -> Callable[[Handler], ToolSpec]:
    """Decorator turning a plain function into a declarative ToolSpec.

    Example:
        @tool("get_current_datetime", "Current time, ISO 8601.", access_kind="read")
        def now(ctx: ToolContext, args: Mapping[str, Any]) -> str: ...
    """

    def decorator(fn: Handler) -> ToolSpec:
        return ToolSpec(
            name=name,
            description=description,
            parameters_schema=dict(schema) if schema else {"type": "object", "properties": {}},
            access_kind=access_kind,
            handler=fn,
        )

    return decorator
