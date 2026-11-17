"""Agent identity and versioned workflow skills (SOUL, AGENTS, SKILL.md).

This package holds git-gated procedure markdown and a pure loader. It must not
import application or infrastructure. Application services compose these texts
into the system prompt; tools still run only through ToolRegistry.
"""

from __future__ import annotations

from personal_agent.agent.compose import ComposedProcedures, compose_procedures
from personal_agent.agent.loader import Skill, list_skills, load_identity, match_skills

__all__ = [
    "ComposedProcedures",
    "Skill",
    "compose_procedures",
    "list_skills",
    "load_identity",
    "match_skills",
]
