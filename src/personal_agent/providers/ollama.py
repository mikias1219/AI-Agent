"""Ollama adapter — the only file that knows Ollama's wire format.

Uses the plain HTTP API (`/api/chat`, non-streaming) so the rest of the app stays
request/response-shaped. Streaming is a later, provider-local enhancement.

Replacing Ollama with a hosted vendor = a new adapter here; nothing above changes.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

import httpx

from personal_agent.core.errors import ProviderError
from personal_agent.core.ports import ModelProvider  # noqa: F401 — for type docs; see protocol in ports
from personal_agent.core.types import AssistantTurn, Message, ToolCall, ToolSpec
from personal_agent.providers.base import ProviderConfig, ollama_message, ollama_tool, retrying

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Implements `core.ports.ModelProvider` against a local Ollama server."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        config: ProviderConfig | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._config = config or ProviderConfig(model_name="llama3.1")
        self._client = httpx.Client(timeout=self._config.timeout_seconds)

    def __repr__(self) -> str:
        return f"OllamaProvider(base_url={self._base!r}, model={self._config.model_name!r})"

    def chat(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> AssistantTurn:
        """Generate one assistant turn; raises ProviderError on any failure."""
        payload: dict[str, object] = {
            "model": self._config.model_name,
            "messages": [ollama_message(m) for m in messages],
            "stream": False,
            "options": {"temperature": 0.6},
        }
        if tools:
            payload["tools"] = [ollama_tool(t) for t in tools]

        def do_call() -> AssistantTurn:
            return self._parse(self._post(payload))

        return retrying("chat", self._config, do_call)  # type: ignore[return-value]

    # -- internals -----------------------------------------------------------

    def _post(self, payload: dict[str, object]) -> dict[str, object]:
        try:
            response = self._client.post(f"{self._base}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        if not isinstance(data, dict):
            raise ProviderError("Ollama returned a non-object response.")
        return data

    def _parse(self, data: Mapping[str, object]) -> AssistantTurn:
        message = data.get("message")
        if not isinstance(message, Mapping):
            raise ProviderError("Ollama response has no 'message' object.")
        content = str(message.get("content", "") or "")
        calls: list[ToolCall] = []
        raw_calls = message.get("tool_calls") or []
        for i, raw in enumerate(raw_calls if isinstance(raw_calls, list) else []):
            if not isinstance(raw, Mapping):
                continue
            fn = raw.get("function") or {}
            if not isinstance(fn, Mapping):
                continue
            calls.append(
                ToolCall(
                    id=str(raw.get("id") or f"call_{len(calls)}_{i}"),
                    name=str(fn.get("name", "")),
                    arguments=(
                        dict(fn.get("arguments"))
                        if isinstance(fn.get("arguments"), Mapping)
                        else {}
                    ),
                )
            )
        return AssistantTurn(content=content, tool_calls=tuple(calls))
