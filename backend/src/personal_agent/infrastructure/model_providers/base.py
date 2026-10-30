"""Shared plumbing for model-provider adapters.

Shared provider configuration, retry behavior, and Ollama wire-format helpers.
The concrete provider adapters own HTTP requests and response handling.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from personal_agent.domain.exceptions import ProviderError
from personal_agent.domain.models import Message, ToolSpec

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Vendor-agnostic knobs every adapter accepts via its constructor."""

    model_name: str
    timeout_seconds: float = 60.0
    max_turn_retries: int = 2
    context_tokens: int = 4096
    max_output_tokens: int = 256
    keep_alive: str = "10m"


def retrying(call: str, config: ProviderConfig, fn: callable) -> object:
    """Run a provider HTTP-ish operation with small retries and ProviderError wrapping."""
    last_error: Exception | None = None
    for attempt in range(1, config.max_turn_retries + 1):
        try:
            return fn()
        except ProviderError:
            raise  # semantic failures are not retried
        except Exception as exc:  # noqa: BLE001 — translated below, never swallowed
            last_error = exc
            logger.warning("Provider '%s' attempt %d failed: %s", call, attempt, exc)
            if attempt < config.max_turn_retries:
                time.sleep(min(2.0 * attempt, 5.0))
    raise ProviderError(
        f"Provider call '{call}' failed after {attempt} attempt(s): {last_error}"
    ) from last_error


def ollama_message(msg: Message) -> dict:
    """Convert one domain message to Ollama's `/api/chat` wire format."""
    wire: dict = {"role": msg.role, "content": msg.content}
    if msg.name:
        wire["name"] = msg.name
    if msg.tool_call_id:
        wire["tool_call_id"] = msg.tool_call_id
    if msg.role == "tool":
        wire.pop("name", None)
    if msg.tool_calls:
        wire["tool_calls"] = [
            {"id": c.id, "function": {"name": c.name, "arguments": c.arguments}}
            for c in msg.tool_calls
        ]
    return wire


def ollama_tool(spec: ToolSpec) -> dict:
    """Convert one tool spec to the provider-facing JSON description sent to the model."""
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": dict(spec.parameters_schema),
        },
    }
