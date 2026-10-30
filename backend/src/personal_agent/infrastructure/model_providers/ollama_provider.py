"""Ollama adapter — the only file that knows Ollama's wire format.

Uses /api/chat for complete turns or incremental text callbacks.
Tool calls are assembled before they reach the controlled execution gate.

Replacing Ollama with a hosted vendor = a new adapter here; nothing above changes.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Mapping, Sequence

import httpx

from personal_agent.domain.exceptions import ProviderError
from personal_agent.domain.models import AssistantTurn, Message, ToolCall, ToolSpec
from personal_agent.domain.ports import ModelProvider  # noqa: F401 — for type docs; see protocol in ports
from personal_agent.infrastructure.model_providers.base import (
    ProviderConfig,
    ollama_message,
    ollama_tool,
    retrying,
)

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Implements `domain.ports.ModelProvider` against a local Ollama server."""

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

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        on_token: Callable[[str], None] | None = None,
    ) -> AssistantTurn:
        """Generate one assistant turn; raises ProviderError on any failure."""
        payload: dict[str, object] = {
            "model": self._config.model_name,
            "messages": [ollama_message(m) for m in messages],
            "stream": on_token is not None,
            "keep_alive": self._config.keep_alive,
            "options": {
                "temperature": 0.4,
                "num_ctx": self._config.context_tokens,
                "num_predict": self._config.max_output_tokens,
            },
        }
        if tools:
            payload["tools"] = [ollama_tool(t) for t in tools]

        if on_token is not None:
            return self._stream(payload, on_token)

        def do_call() -> AssistantTurn:
            return self._parse(self._post(payload))

        return retrying("chat", self._config, do_call)  # type: ignore[return-value]

    # -- internals -----------------------------------------------------------

    def _stream(self, payload: dict, on_token: Callable[[str], None]) -> AssistantTurn:
        content, calls = [], []
        started = time.monotonic()
        try:
            with self._client.stream("POST", f"{self._base}/api/chat", json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if not isinstance(chunk, dict) or chunk.get("error"):
                        raise ProviderError("Ollama could not complete the streamed response.")
                    message = chunk.get("message") or {}
                    if not isinstance(message, Mapping):
                        raise ProviderError("Ollama returned an invalid message chunk.")
                    text = message.get("content", "")
                    if not isinstance(text, str):
                        raise ProviderError("Ollama returned invalid text.")
                    if text:
                        content.append(text)
                        on_token(text)
                    calls.extend(message.get("tool_calls") or [])
                    if chunk.get("done"):
                        logger.info(
                            "Model reply: %.1fs, %s output tokens, %.1fs loading.",
                            time.monotonic() - started,
                            chunk.get("eval_count", 0),
                            chunk.get("load_duration", 0) / 1e9,
                        )
                        return self._parse(
                            {
                                "message": {"content": "".join(content), "tool_calls": calls},
                                "done_reason": chunk.get("done_reason"),
                            }
                        )
        except (httpx.HTTPError, ValueError) as exc:
            # Never replay a stream after partial output or tool actions.
            raise ProviderError("Ollama stream failed. Check the local model service.") from exc
        raise ProviderError("Ollama ended the stream before completing the response.")

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
        if data.get("done_reason") == "length" and not calls:
            content += "\n\n(Reply length limit reached. Ask me to continue.)"
        return AssistantTurn(content=content, tool_calls=tuple(calls))
