"""OpenAI-compatible provider parses chat completions."""

from __future__ import annotations

import json

import httpx

from personal_agent.domain.models import Message
from personal_agent.infrastructure.model_providers.base import ProviderConfig
from personal_agent.infrastructure.model_providers.openai_compatible import (
    OpenAICompatibleProvider,
)


def test_chat_returns_assistant_content():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        assert request.headers.get("Authorization") == "Bearer gsk_test"
        body = json.loads(request.content)
        assert body["model"] == "llama-3.1-8b-instant"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "I can help with that task.",
                        }
                    }
                ]
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://api.groq.com/openai/v1",
        api_key="gsk_test",
        config=ProviderConfig(model_name="llama-3.1-8b-instant", max_output_tokens=256),
    )
    provider._client = httpx.Client(transport=httpx.MockTransport(handler), timeout=30.0)

    turn = provider.chat([Message(role="user", content="Help me")], tools=())
    assert turn.content == "I can help with that task."
    assert turn.tool_calls == ()
