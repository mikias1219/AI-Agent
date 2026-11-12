"""Fast/smart model roles with provider fallback (AGT-07)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from personal_agent.application.tools.selection import parse_group_list
from personal_agent.domain.exceptions import AgentError
from personal_agent.domain.models import AssistantTurn, Message, ToolSpec
from personal_agent.domain.ports import ModelProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ModelRoleConfig:
    role: str  # fast | smart
    label: str
    provider: ModelProvider


class ModelRouter:
    """Routes lightweight jobs to fast, reasoning to smart, with fallback on errors."""

    def __init__(
        self,
        *,
        fast: ModelProvider,
        smart: ModelProvider,
        fast_label: str = "fast",
        smart_label: str = "smart",
        fallback: Sequence[ModelProvider] | None = None,
    ) -> None:
        self._fast = fast
        self._smart = smart
        self._fast_label = fast_label
        self._smart_label = smart_label
        self._fallback = list(fallback or ())

    @property
    def roles(self) -> dict[str, str]:
        return {"fast": self._fast_label, "smart": self._smart_label}

    def chat(
        self,
        role: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
        on_token: Callable[[str], None] | None = None,
    ) -> AssistantTurn:
        primary = self._smart if role == "smart" else self._fast
        chain = [primary, *[p for p in self._fallback if p is not primary]]
        last_error: Exception | None = None
        for provider in chain:
            try:
                return provider.chat(messages, tools, on_token=on_token)
            except AgentError as exc:
                last_error = exc
                logger.warning("Provider failed for role=%s: %s", role, exc)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Provider error for role=%s: %s", role, exc)
        raise AgentError(f"All providers failed for role '{role}'.") from last_error

    def choose_tool_groups(self, available: Sequence[str]) -> list[str]:
        prompt = (
            "Select which tool integration groups are needed. "
            f"Available groups: {list(available)}. "
            'Reply with JSON only: {"groups": ["core", "..."]}.'
        )
        turn = self.chat(
            "fast",
            [Message(role="user", content=prompt)],
            tools=(),
        )
        chosen = parse_group_list(turn.content or "", available)
        return chosen or list(available)


class RoutingProvider:
    """ModelProvider that always uses the smart role (agent loop default)."""

    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        on_token: Callable[[str], None] | None = None,
    ) -> AssistantTurn:
        return self._router.chat("smart", messages, tools, on_token=on_token)
