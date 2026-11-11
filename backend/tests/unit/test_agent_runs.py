"""Unit: run events, cancel, BR-09 limits and prompt versions through ChatService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from personal_agent.application.agent import Agent
from personal_agent.application.run_events import FanoutSink, RecordingEventSink, RunStepRecorder
from personal_agent.application.services.chat_service import ChatService
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.domain.exceptions import ProviderError
from personal_agent.domain.models import (
    AssistantTurn,
    CancellationToken,
    Message,
    OwnerProfile,
    RunStatus,
    StepStatus,
    ToolCall,
    ToolContext,
    ToolSpec,
)
from personal_agent.infrastructure.persistence.repositories import (
    AgentRunRepositoryImpl,
    OwnerProfileRepositoryImpl,
)
from tests.conftest import make_spy_tool

NOW = datetime(2026, 11, 11, 22, 30, tzinfo=UTC)  # already Nov 12 in Nairobi


@pytest.fixture()
def run_repo(session_factory) -> AgentRunRepositoryImpl:
    return AgentRunRepositoryImpl(session_factory)


@pytest.fixture()
def sink() -> RecordingEventSink:
    return RecordingEventSink()


@pytest.fixture()
def profiles(session_factory) -> ProfileService:
    return ProfileService(OwnerProfileRepositoryImpl(session_factory))


@pytest.fixture()
def service(agent, conversations, memory_store, audit_log, run_repo, sink, profiles) -> ChatService:
    return ChatService(
        agent=agent,
        conversations=conversations,
        memory=memory_store,
        audit=audit_log,
        runs=run_repo,
        events=FanoutSink([RunStepRecorder(run_repo), sink]),
        profiles=profiles,
        clock=lambda: NOW,
    )


def _call(call_id: str, name: str) -> AssistantTurn:
    return AssistantTurn(tool_calls=(ToolCall(id=call_id, name=name, arguments={}),))


def _only_run(run_repo: AgentRunRepositoryImpl):
    (run,) = run_repo.list_recent()
    return run


def test_event_order_for_a_tool_turn(service, scripted_provider, tool_registry, sink, run_repo):
    tool_registry.register(make_spy_tool("report_time", output="12:00"))
    scripted_provider._script = [_call("c1", "report_time"), AssistantTurn(content="It is 12:00.")]

    service.turn(user_id="u", text="time?", on_token=lambda _t: None)

    assert sink.types == ["run.started", "tool.started", "tool.finished", "token", "run.completed"]
    started, _, finished, _, completed = sink.events
    assert started.data["prompt_version"].startswith("system_v1@")
    assert finished.data["ok"] is True and finished.data["output"] == "12:00"
    assert completed.data["reply"] == "It is 12:00."
    assert {e.run_id for e in sink.events} == {_only_run(run_repo).id}


def test_steps_are_persisted_with_timings(service, scripted_provider, tool_registry, run_repo):
    tool_registry.register(make_spy_tool("report_time", output="12:00"))
    scripted_provider._script = [_call("c1", "report_time"), AssistantTurn(content="done")]

    service.turn(user_id="u", text="time?")

    run = _only_run(run_repo)
    (step,) = run_repo.list_steps(run.id)
    assert (step.name, step.status, step.output) == ("report_time", StepStatus.OK, "12:00")
    assert step.duration_ms is not None and step.finished_at is not None
    assert (run.status, run.final_text, run.finished_at) == (RunStatus.COMPLETED, "done", NOW)


def test_blocked_tool_is_a_failed_step_and_run_still_completes(
    service, scripted_provider, sink, run_repo
):
    scripted_provider._script = [_call("c1", "ghost"), AssistantTurn(content="Handled.")]

    service.turn(user_id="u", text="x")

    finished = next(e for e in sink.events if e.type == "tool.finished")
    assert finished.data["ok"] is False
    (step,) = run_repo.list_steps(_only_run(run_repo).id)
    assert step.status is StepStatus.FAILED and "no tool named" in step.error.lower()


def test_approval_events_are_emitted_on_the_run(
    service, scripted_provider, tool_registry, sink, run_repo
):
    tool_registry.register(make_spy_tool("send_it", access_kind="execute"))
    scripted_provider._script = [_call("c1", "send_it"), AssistantTurn(content="Waiting.")]

    service.turn(user_id="u", text="send")

    assert sink.types == [
        "run.started",
        "tool.started",
        "approval.required",
        "approval.resolved",
        "tool.finished",
        "run.completed",
    ]
    required, resolved = (e for e in sink.events if e.type.startswith("approval."))
    assert required.data["approval_id"] == resolved.data["approval_id"]
    assert resolved.data["decision"] == "deferred"


def test_provider_failure_marks_run_failed(service, scripted_provider, sink, run_repo):
    class Boom:
        def chat(self, *_a, **_k):
            raise ProviderError("model offline")

    service._agent._provider = Boom()

    with pytest.raises(ProviderError):
        service.turn(user_id="u", text="hi")

    run = _only_run(run_repo)
    assert (run.status, run.error) == (RunStatus.FAILED, "model offline")
    assert sink.types == ["run.started", "run.failed"]
    assert sink.events[-1].data == {"status": "failed", "error": "model offline"}


def test_cancel_between_steps_skips_remaining_tools(
    service, scripted_provider, tool_registry, sink, run_repo, conversations
):
    token = CancellationToken()
    ran: list[str] = []

    def make(name: str, cancel_after: bool) -> ToolSpec:
        def handler(_ctx, _args) -> str:
            ran.append(name)
            if cancel_after:
                token.cancel()
            return f"{name} ok"

        return ToolSpec(name, name, {"type": "object", "properties": {}}, "read", handler)

    tool_registry.register_all([make("first", True), make("second", False)])
    scripted_provider._script = [
        AssistantTurn(
            tool_calls=(
                ToolCall(id="c1", name="first", arguments={}),
                ToolCall(id="c2", name="second", arguments={}),
            )
        ),
        AssistantTurn(content="never reached"),
    ]

    session_id, reply = service.turn(user_id="u", text="go", cancel=token)

    assert ran == ["first"]  # the second step never started
    assert sink.types == ["run.started", "tool.started", "tool.finished", "run.failed"]
    assert sink.events[-1].data["status"] == "cancelled"
    run = _only_run(run_repo)
    assert run.status is RunStatus.CANCELLED and run.stop_reason == "cancelled"
    assert "first" in reply and "second (not run)" in reply
    # History stays valid: every tool call has a tool message, then the summary.
    saved = conversations.load(session_id)
    assert [m.role for m in saved] == ["user", "assistant", "tool", "tool", "assistant"]
    assert saved[3].content.startswith("Not run:")
    assert scripted_provider.calls and len(scripted_provider.calls) == 1


def test_cancel_before_first_model_call(service, scripted_provider, sink, run_repo):
    token = CancellationToken()
    token.cancel()

    service.turn(user_id="u", text="go", cancel=token)

    assert scripted_provider.calls == []
    assert _only_run(run_repo).status is RunStatus.CANCELLED


def test_cancel_during_streaming_aborts_the_model_call(service, run_repo, sink):
    token = CancellationToken()

    class Streaming:
        def chat(self, messages, tools, on_token=None):
            on_token("Hel")
            token.cancel()
            on_token("lo")  # raises RunCancelledError inside the agent's wrapper
            return AssistantTurn(content="Hello")

    service._agent._provider = Streaming()

    _, reply = service.turn(user_id="u", text="hi", cancel=token)

    assert sink.types == ["run.started", "token", "run.failed"]
    assert "asked me to" in reply
    assert _only_run(run_repo).status is RunStatus.CANCELLED


def test_round_limit_produces_progress_summary(
    service, scripted_provider, tool_registry, sink, run_repo
):
    tool_registry.register(make_spy_tool("step", output="did a thing"))
    scripted_provider._script = [_call(f"c{i}", "step") for i in range(10)]
    service._agent._max_tool_rounds = 3

    _, reply = service.turn(user_id="u", text="loop")

    assert len(scripted_provider.calls) == 3
    assert "stopped after 3 tool rounds" in reply
    assert "Done so far" in reply and "step: did a thing" in reply
    assert "Still to do" in reply and "continue" in reply
    run = _only_run(run_repo)
    assert (run.status, run.stop_reason) == (RunStatus.COMPLETED, "limit_rounds")
    assert sink.events[-1].type == "run.completed"
    assert sink.events[-1].data["stop_reason"] == "limit_rounds"


def test_default_limits_follow_br09():
    from personal_agent.application.agent import DEFAULT_MAX_SECONDS, DEFAULT_MAX_TOOL_ROUNDS

    assert (DEFAULT_MAX_TOOL_ROUNDS, DEFAULT_MAX_SECONDS) == (6, 90.0)


def test_time_limit_stops_between_tools_and_lists_remaining(scripted_provider, tool_registry, ctx):
    now = [0.0]

    def handler(_ctx, _args) -> str:
        now[0] += 100  # the first tool burns the whole budget
        return "slow done"

    tool_registry.register_all(
        [
            ToolSpec("slow", "slow", {"type": "object", "properties": {}}, "read", handler),
            make_spy_tool("later"),
        ]
    )
    agent = Agent(
        provider=scripted_provider,
        registry=tool_registry,
        max_seconds=90,
        clock=lambda: now[0],
    )
    scripted_provider._script = [
        AssistantTurn(
            tool_calls=(
                ToolCall(id="c1", name="slow", arguments={}),
                ToolCall(id="c2", name="later", arguments={}),
            )
        )
    ]

    outcome = agent.run_turn([Message(role="user", content="go")], ctx)

    assert outcome.stop_reason == "limit_time"
    assert "stopped after 90 seconds" in outcome.final_text
    assert "slow: slow done" in outcome.final_text
    assert "later (not run)" in outcome.final_text


def test_prompt_version_stored_with_date_timezone_and_language(
    service, scripted_provider, profiles, run_repo
):
    profiles.update("u", timezone="Africa/Nairobi", language="sw", name="Mikias")

    service.turn(user_id="u", text="hi")

    run = _only_run(run_repo)
    assert run.prompt_version == "system_v1@2026-11-12/Africa/Nairobi/sw"
    system = scripted_provider.calls[0][0][0]
    assert system.role == "system"
    assert "2026-11-12" in system.content and "Africa/Nairobi" in system.content
    assert "sw" in system.content and "Mikias" in system.content


def test_prompt_defaults_to_utc_and_english(service, run_repo):
    service.turn(user_id="nobody", text="hi")
    assert _only_run(run_repo).prompt_version == "system_v1@2026-11-11/UTC/en"


def test_blank_input_starts_no_run(service, run_repo, sink):
    session_id, reply = service.turn(user_id="u", text="   ")
    assert (reply, run_repo.list_recent(), sink.events) == ("", [], [])
    assert session_id


def test_owner_profile_default_language_is_english():
    assert OwnerProfile(owner_id="x").language == "en"
    assert ToolContext(user_id="u", session_id="s", origin="cli").events is None
