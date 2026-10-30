"""Incremental responses must preserve text/tool calls without replaying failed streams."""

import json

import httpx
import pytest

from personal_agent.domain.exceptions import ProviderError
from personal_agent.domain.models import Message
from personal_agent.infrastructure.model_providers.base import ProviderConfig
from personal_agent.infrastructure.model_providers.ollama_provider import OllamaProvider


def test_stream_emits_chunks_and_preserves_tool_requests():
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        frames = [
            {"message": {"content": "Hello "}},
            {"message": {"content": "there"}},
            {
                "message": {"tool_calls": [{"function": {"name": "task_list", "arguments": {}}}]},
                "done": True,
            },
        ]
        return httpx.Response(200, content="\n".join(json.dumps(f) for f in frames))

    provider = OllamaProvider(config=ProviderConfig(model_name="test"))
    provider._client = httpx.Client(transport=httpx.MockTransport(handler))
    chunks = []
    turn = provider.chat([Message(role="user", content="hi")], [], on_token=chunks.append)
    assert chunks == ["Hello ", "there"]
    assert turn.content == "Hello there"
    assert turn.tool_calls[0].name == "task_list"
    assert captured[0]["stream"] is True
    assert captured[0]["options"]["num_predict"] == 256
    assert captured[0]["keep_alive"] == "10m"


def test_incomplete_stream_is_not_retried_after_partial_text():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=json.dumps({"message": {"content": "partial"}}) + "\n")

    provider = OllamaProvider(config=ProviderConfig(model_name="test", max_turn_retries=3))
    provider._client = httpx.Client(transport=httpx.MockTransport(handler))
    chunks = []
    with pytest.raises(ProviderError, match="before completing"):
        provider.chat([Message(role="user", content="hi")], [], on_token=chunks.append)
    assert chunks == ["partial"]
    assert len(requests) == 1


def test_limited_reply_explains_that_the_model_hit_its_budget():
    provider = OllamaProvider()
    turn = provider._parse({"message": {"content": "Partial response"}, "done_reason": "length"})
    assert "Reply length limit reached" in turn.content
