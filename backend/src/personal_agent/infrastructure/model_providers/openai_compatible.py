"""OpenAI-compatible chat adapter (Groq, OpenRouter, Gemini OpenAI mode, etc.).

Used for production inference when local Ollama is unreachable (e.g. Render).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence

import httpx

from personal_agent.domain.exceptions import ProviderError
from personal_agent.domain.models import AssistantTurn, Message, ToolCall, ToolSpec
from personal_agent.infrastructure.model_providers.base import ProviderConfig, retrying

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider:
    """Implements ModelProvider against `/v1/chat/completions`."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        config: ProviderConfig | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._config = config or ProviderConfig(model_name="llama-3.1-8b-instant")
        self._client = httpx.Client(timeout=self._config.timeout_seconds)

    def __repr__(self) -> str:
        return (
            f"OpenAICompatibleProvider(base_url={self._base!r}, model={self._config.model_name!r})"
        )

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        on_token: Callable[[str], None] | None = None,
    ) -> AssistantTurn:
        payload: dict[str, object] = {
            "model": self._config.model_name,
            "messages": [_wire_message(m) for m in messages],
            "temperature": 0.4,
            "max_tokens": self._config.max_output_tokens,
            "stream": on_token is not None,
        }
        if tools:
            payload["tools"] = [_wire_tool(t) for t in tools]
            payload["tool_choice"] = "auto"

        if on_token is not None:
            return self._stream(payload, on_token)

        def do_call() -> AssistantTurn:
            response = self._post(payload)
            return self._parse_complete(response)

        return retrying("chat", self._config, do_call)  # type: ignore[return-value]

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _post(self, payload: dict[str, object]) -> dict:
        url = f"{self._base}/chat/completions"
        try:
            response = self._client.post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Inference request failed: {exc}") from exc
        if response.status_code >= 400:
            detail = response.text[:400]
            raise ProviderError(f"Inference HTTP {response.status_code}: {detail}")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError("Inference returned invalid JSON.") from exc

    def _stream(self, payload: dict[str, object], on_token: Callable[[str], None]) -> AssistantTurn:
        url = f"{self._base}/chat/completions"
        content: list[str] = []
        tool_acc: dict[int, dict[str, str]] = {}
        try:
            with self._client.stream(
                "POST", url, headers=self._headers(), json=payload
            ) as response:
                if response.status_code >= 400:
                    body = response.read().decode("utf-8", errors="replace")[:400]
                    raise ProviderError(f"Inference HTTP {response.status_code}: {body}")
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except ValueError:
                        continue
                    choice = (chunk.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    piece = delta.get("content") or ""
                    if piece:
                        content.append(piece)
                        on_token(piece)
                    for call in delta.get("tool_calls") or []:
                        idx = int(call.get("index", 0))
                        slot = tool_acc.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                        if call.get("id"):
                            slot["id"] = call["id"]
                        fn = call.get("function") or {}
                        if fn.get("name"):
                            slot["name"] = fn["name"]
                        if fn.get("arguments"):
                            slot["arguments"] += fn["arguments"]
        except ProviderError:
            raise
        except httpx.HTTPError as exc:
            raise ProviderError(f"Inference stream failed: {exc}") from exc

        calls = tuple(
            ToolCall(
                id=slot["id"] or f"call_{idx}",
                name=slot["name"],
                arguments=_parse_args(slot["arguments"]),
            )
            for idx, slot in sorted(tool_acc.items())
            if slot["name"]
        )
        return AssistantTurn(content="".join(content), tool_calls=calls)

    def _parse_complete(self, payload: dict) -> AssistantTurn:
        try:
            message = (payload.get("choices") or [{}])[0].get("message") or {}
        except (TypeError, IndexError, AttributeError) as exc:
            raise ProviderError("Unexpected inference response shape.") from exc
        content = message.get("content") or ""
        calls = []
        for raw in message.get("tool_calls") or []:
            fn = raw.get("function") or {}
            name = fn.get("name") or ""
            if not name:
                continue
            calls.append(
                ToolCall(
                    id=raw.get("id") or f"call_{len(calls)}",
                    name=name,
                    arguments=_parse_args(fn.get("arguments") or "{}"),
                )
            )
        return AssistantTurn(content=content, tool_calls=tuple(calls))


def _wire_message(msg: Message) -> dict:
    wire: dict = {"role": msg.role, "content": msg.content}
    if msg.role == "tool":
        wire["tool_call_id"] = msg.tool_call_id or ""
        if msg.name:
            wire["name"] = msg.name
    if msg.tool_calls:
        wire["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {
                    "name": c.name,
                    "arguments": json.dumps(c.arguments, ensure_ascii=False),
                },
            }
            for c in msg.tool_calls
        ]
    return wire


def _wire_tool(spec: ToolSpec) -> dict:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": dict(spec.parameters_schema),
        },
    }


def _parse_args(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {"_raw": raw}
    return parsed if isinstance(parsed, dict) else {"_raw": raw}
