"""ModelRouter fast/smart roles and fallback (R3)."""

from __future__ import annotations

from personal_agent.application.model_router import ModelRouter
from personal_agent.domain.exceptions import AgentError
from personal_agent.domain.models import Message
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider


class _FailingProvider:
    def chat(self, messages, tools, on_token=None):
        raise AgentError("boom")


def test_provider_failure_falls_back() -> None:
    fallback = FakeProvider(script=["recovered"])
    router = ModelRouter(
        fast=_FailingProvider(),  # type: ignore[arg-type]
        smart=_FailingProvider(),  # type: ignore[arg-type]
        fallback=(fallback,),
    )
    turn = router.chat("fast", [Message(role="user", content="hi")])
    assert turn.content == "recovered"


def test_choose_tool_groups_uses_fast_json() -> None:
    fast = FakeProvider(script=['{"groups": ["tasks", "core"]}'])
    router = ModelRouter(fast=fast, smart=FakeProvider())
    groups = router.choose_tool_groups(["core", "tasks", "google", "memory"])
    assert set(groups) == {"tasks", "core"}
