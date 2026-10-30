"""Tool registry and execution gate — THE enforcement point.

Nothing runs unless it passes all four checks here, in order:

1. known tool            (UnknownToolError otherwise)
2. schema-validated args (jsonschema; ToolInputError otherwise)
3. permission policy     (PermissionDeniedError otherwise)
4. human approval        (ApprovalGateway) for `execute`-kind tools, or policy-marked tools
5. audit record          for every decision, always

Handlers raising unexpected exceptions surface as failed ToolResults so a model can
react, while policy/permission rejections *raise* — those are system-level events.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

import jsonschema

from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.domain.exceptions import PermissionDeniedError, ToolInputError, UnknownToolError
from personal_agent.domain.models import (
    ToolCall,
    ToolContext,
    ToolResult,
    ToolSpec,
)
from personal_agent.domain.ports import ApprovalGateway, AuditLog, ToolRegistry

logger = logging.getLogger(__name__)


class ToolRegistryImpl(ToolRegistry):
    """Concrete registry implementing the `domain.ports.ToolRegistry` contract."""

    def __init__(
        self,
        *,
        policy: PermissionPolicy,
        approvals: ApprovalGateway,
        audit: AuditLog,
    ) -> None:
        self._policy = policy
        self._approvals = approvals
        self._audit = audit
        self._specs: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:  # duplicate registrations are a wiring bug
            raise ValueError(f"Tool '{spec.name}' is already registered.")
        self._specs[spec.name] = spec
        logger.debug("Registered tool '%s' (%s).", spec.name, spec.access_kind)

    def register_all(self, specs: list[ToolSpec]) -> None:
        for spec in specs:
            self.register(spec)

    def specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def execute(self, call: ToolCall, ctx: ToolContext) -> ToolResult:
        spec = self._maybe_spec(call.name)
        try:
            args = self._validated_args(spec, call.arguments)
        except ToolInputError as e:
            self._audit.record(
                "tool.input_rejected",
                ctx.user_id,
                {"tool": call.name, "error": str(e), "origin": ctx.origin},
            )
            raise

        if not self._policy.is_allowed(ctx, spec):
            reason = f"Permission policy denies tool '{call.name}'."
            self._audit.record(
                "tool.permission_denied",
                ctx.user_id,
                {"tool": call.name, "reason": reason, "origin": ctx.origin},
            )
            raise PermissionDeniedError(f"Tool '{call.name}' blocked: {reason}") from None

        if self._policy.approval_required(spec):
            decision = self._approvals.request(call, ctx)
            self._audit.record(
                "tool.approval",
                ctx.user_id,
                {"tool": call.name, "decision": decision, "origin": ctx.origin},
            )
            if decision != "approved":
                raise PermissionDeniedError(
                    f"Tool '{call.name}' requires human approval and it was {decision}."
                )

        try:
            output = spec.handler(ctx, args)
        except Exception as exc:  # noqa: BLE001 — turned into model-visible failure
            logger.warning("Tool '%s' handler failed: %s", call.name, exc)
            result = ToolResult(tool_name=call.name, ok=False, error=str(exc))
        else:
            result = ToolResult(tool_name=call.name, ok=True, output=output)

        self._audit.record(
            "tool.executed",
            ctx.user_id,
            {"tool": call.name, "ok": result.ok, "origin": ctx.origin},
        )
        return result

    # -- internals -----------------------------------------------------------

    def _maybe_spec(self, name: str) -> ToolSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise UnknownToolError(f"No tool named '{name}' is registered.") from exc

    def _validated_args(self, spec: ToolSpec, arguments: Mapping[str, Any]) -> dict[str, Any]:
        try:
            jsonschema.validate(instance=dict(arguments), schema=dict(spec.parameters_schema))
        except jsonschema.ValidationError as exc:
            raise ToolInputError(f"Bad arguments for '{spec.name}': {exc.message}") from exc
        except (TypeError, ValueError) as exc:  # non-JSON-izable or ill-formed schema
            raise ToolInputError(f"Unusable schema for '{spec.name}': {exc}") from exc
        return json.loads(json.dumps(dict(arguments)))  # deep-copy plain JSON values
