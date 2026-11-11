"""Versioned system prompts (AGT-08).

Each prompt lives in a `<name>_v<N>.md` file next to this module. `render_system_prompt`
fills in date, timezone, language and profile and returns the text together with a
version id that is stored on every AgentRun, so any answer can be traced to the exact
prompt that produced it. Bump the file version (add `system_v2.md`, change
`CURRENT_SYSTEM_PROMPT`) whenever the wording changes.

This package depends on nothing in the project, so any layer may import it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib import resources

CURRENT_SYSTEM_PROMPT = "system_v1"


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    text: str
    version: str  # e.g. "system_v1@2026-11-11/Africa/Nairobi/en"


@cache
def _template(name: str) -> str:
    return resources.files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")


def render_system_prompt(
    *,
    today: date,
    timezone: str = "UTC",
    language: str = "en",
    owner_name: str | None = None,
    facts: list[str] | None = None,
    name: str = CURRENT_SYSTEM_PROMPT,
) -> RenderedPrompt:
    owner_line = f" The owner's name is {owner_name}." if owner_name else ""
    text = (
        _template(name)
        .format(
            date=today.isoformat(),
            weekday=today.strftime("%A"),
            timezone=timezone,
            language=language,
            owner_line=owner_line,
        )
        .strip()
    )
    if facts:
        lines = "\n".join(f"- {fact}" for fact in facts)
        text += f"\n\nKnown preferences and facts about this user:\n{lines}"
    return RenderedPrompt(text=text, version=f"{name}@{today.isoformat()}/{timezone}/{language}")
