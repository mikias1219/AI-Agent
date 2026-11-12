"""Offline evaluation harness (OBS-03).

Loads JSON scenarios: scripted FakeProvider turns, spy tools, expected/forbidden
tool calls and text. Runs entirely without network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from personal_agent.application.agent import Agent
from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.models import AssistantTurn, Message, ToolCall, ToolContext, ToolSpec
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
)

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    passed: bool
    errors: tuple[str, ...]


def list_scenario_paths() -> list[Path]:
    return sorted(SCENARIOS_DIR.glob("*.json"))


def load_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _make_tool(spec: dict[str, Any]) -> ToolSpec:
    name = str(spec["name"])
    access_kind = str(spec.get("access_kind", "read"))
    fail = spec.get("fail")
    default_output = spec.get("output", f"ran {name}")
    untrusted = bool(spec.get("untrusted_output", False))

    def handler(_ctx: ToolContext, args: dict[str, Any]) -> str:
        if fail:
            raise RuntimeError(str(fail))
        return str(default_output)

    return ToolSpec(
        name=name,
        description=f"eval spy {name}",
        parameters_schema={"type": "object", "properties": {}, "additionalProperties": True},
        access_kind=access_kind,  # type: ignore[arg-type]
        handler=handler,
        untrusted_output=untrusted,
    )


def _script_turn(item: dict[str, Any]) -> AssistantTurn:
    if "tool_calls" in item:
        calls = tuple(
            ToolCall(
                id=str(c["id"]),
                name=str(c["name"]),
                arguments=dict(c.get("arguments") or {}),
            )
            for c in item["tool_calls"]
        )
        return AssistantTurn(content=str(item.get("content") or ""), tool_calls=calls)
    return AssistantTurn(content=str(item.get("content") or ""))


def run_scenario(scenario: dict[str, Any], session_factory) -> ScenarioResult:
    sid = str(scenario["id"])
    errors: list[str] = []
    audit = AuditLogImpl(session_factory)
    repo = ApprovalRepositoryImpl(session_factory)
    registry = ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=ApprovalGatewayImpl(repo=repo, audit=audit, durable=True),
        audit=audit,
    )
    for tool in scenario.get("tools") or []:
        registry.register(_make_tool(tool))

    provider = FakeProvider(script=[_script_turn(t) for t in scenario.get("script") or []])
    max_rounds = int(scenario.get("max_tool_rounds", 6))
    agent = Agent(provider=provider, registry=registry, max_tool_rounds=max_rounds)

    ctx_data = dict(scenario.get("context") or {})
    ctx = ToolContext(
        user_id=str(ctx_data.get("user_id", "tester")),
        session_id=str(ctx_data.get("session_id", "sess-eval")),
        origin=str(ctx_data.get("origin", "cli")),
    )
    outcome = agent.run_turn([Message(role="user", content=str(scenario["input"]))], ctx)
    expect = dict(scenario.get("expect") or {})

    made = [c.name for c in outcome.tool_calls_made]
    if "tool_calls" in expect:
        wanted = list(expect["tool_calls"])
        if made != wanted:
            errors.append(f"tool_calls={made!r} expected {wanted!r}")

    for name in expect.get("forbidden_executed") or []:
        if name in made:
            errors.append(f"forbidden tool executed: {name}")

    text = outcome.final_text or ""
    text_l = text.lower()
    for needle in expect.get("text_contains") or []:
        if needle.lower() not in text_l:
            errors.append(f"missing text {needle!r} in {text!r}")
    for needle in expect.get("text_not_contains") or []:
        if needle.lower() in text_l:
            errors.append(f"forbidden text {needle!r} in {text!r}")

    if "stop_reason" in expect:
        wanted_stop = expect["stop_reason"]
        if outcome.stop_reason != wanted_stop:
            errors.append(f"stop_reason={outcome.stop_reason!r} expected {wanted_stop!r}")

    return ScenarioResult(scenario_id=sid, passed=not errors, errors=tuple(errors))
