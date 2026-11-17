"""Compose SOUL / AGENTS / matched skills into a system-prompt appendix."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from personal_agent.agent.loader import (
    IdentityDoc,
    Skill,
    list_skills,
    load_identity,
    match_skills,
)

logger = logging.getLogger(__name__)

_NEVER_HEADING = re.compile(r"^## Never\b", re.M)
_CHAR_HEADING = re.compile(r"^## Character\b", re.M)


_SOFT_PLAN_SKILLS = frozenset({"inbox-to-action", "plan-my-time"})

_SOFT_PLAN_HINT = """# Soft plan for this turn

Before calling tools, briefly list numbered steps you will take (what to read,
what to draft, what needs approval). Keep it short. Then follow the skill
Procedure. Do not claim a COMMIT finished until a tool succeeds after approval."""


@dataclass(frozen=True, slots=True)
class ComposedProcedures:
    text: str
    version_suffix: str  # e.g. "+soul@1.0.0+skills:remind-and-follow-up@1.0.0"
    skills: tuple[Skill, ...]

    @property
    def tool_groups(self) -> frozenset[str]:
        groups: set[str] = set()
        for skill in self.skills:
            groups.update(skill.tool_groups)
        return frozenset(groups)


def _compact_soul(doc: IdentityDoc) -> str:
    text = doc.text
    if len(text) <= 2500:
        return text
    parts: list[str] = []
    for pattern in (_CHAR_HEADING, _NEVER_HEADING):
        m = pattern.search(text)
        if not m:
            continue
        start = m.start()
        nxt = text.find("\n## ", start + 3)
        parts.append(text[start:] if nxt < 0 else text[start:nxt])
    return "\n\n".join(parts).strip() or text[:2500]


def _compact_agents(doc: IdentityDoc) -> str:
    text = doc.text
    if len(text) <= 2000:
        return text
    # Prefer end-states section if present
    marker = "## Every run ends"
    idx = text.find(marker)
    if idx < 0:
        marker = "## Run end states"
        idx = text.find(marker)
    if idx >= 0:
        return text[idx:].strip()
    return text[:2000]


def compose_procedures(
    user_text: str = "",
    *,
    origin: str | None = None,
    limit: int = 2,
    skills: tuple[Skill, ...] | None = None,
    identity: tuple[IdentityDoc, IdentityDoc] | None = None,
) -> ComposedProcedures:
    """Build the procedure block and a version suffix for prompt_version."""
    try:
        soul, agents = identity if identity is not None else load_identity()
    except Exception:  # noqa: BLE001
        logger.exception("Could not load SOUL/AGENTS; continuing without them")
        return ComposedProcedures(text="", version_suffix="", skills=())

    catalog = skills if skills is not None else list_skills()
    matched = tuple(match_skills(user_text, origin=origin, limit=limit, skills=catalog))

    blocks = [
        "# AURA identity (SOUL)\n\n" + _compact_soul(soul),
        "# Operating instructions\n\n" + _compact_agents(agents),
    ]
    for skill in matched:
        blocks.append(f"# Skill: {skill.name}\n\n{skill.body.strip()}")
    if any(s.name in _SOFT_PLAN_SKILLS for s in matched):
        blocks.append(_SOFT_PLAN_HINT)

    version = f"+soul@{soul.version}"
    if matched:
        skill_part = ",".join(f"{s.name}@{s.version}" for s in matched)
        version += f"+skills:{skill_part}"

    return ComposedProcedures(
        text="\n\n".join(blocks).strip(),
        version_suffix=version,
        skills=matched,
    )
