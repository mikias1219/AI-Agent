"""Load SOUL, AGENTS, and SKILL.md files from the agent package tree."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    description: str
    version: str
    body: str
    tags: tuple[str, ...] = ()
    workflow: str = ""
    tool_groups: tuple[str, ...] = ()
    path: Path | None = None
    when_text: str = ""


@dataclass(frozen=True, slots=True)
class IdentityDoc:
    kind: str  # "soul" | "agents"
    version: str
    text: str


def _package_root() -> Path:
    return Path(str(resources.files(__package__)))


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end < 0:
        raise ValueError("unclosed YAML frontmatter")
    raw = rest[:end]
    body = rest[end + 5 :]
    return _parse_simple_yaml(raw), body.lstrip("\n")


def _parse_simple_yaml(raw: str) -> dict[str, Any]:
    """Minimal YAML subset for skill/identity frontmatter (no PyYAML dependency)."""
    root: dict[str, Any] = {}
    # stack entries: indent level where this map's *keys* are written
    stack: list[tuple[int, dict[str, Any]]] = [(0, root)]
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError(f"bad indent: {line!r}")
        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        if indent != stack[-1][0]:
            raise ValueError(f"bad indent: {line!r}")
        key, _, value = line.strip().partition(":")
        key, value = key.strip(), value.strip()
        current = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            current[key] = child
            stack.append((indent + 2, child))
        else:
            current[key] = _parse_scalar(value)
    return root


def _parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _section(body: str, heading: str) -> str:
    marker = f"## {heading}"
    start = body.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    nxt = body.find("\n## ", start)
    chunk = body[start:] if nxt < 0 else body[start:nxt]
    return chunk.strip()


def _tokens(text: str) -> set[str]:
    return {m.group(0) for m in _TOKEN.finditer(text.lower()) if len(m.group(0)) > 2}


def parse_skill_text(text: str, *, path: Path | None = None) -> Skill:
    meta, body = _split_frontmatter(text)
    name = str(meta.get("name") or "")
    description = str(meta.get("description") or "")
    version = str(meta.get("version") or "1.0.0")
    aura = (meta.get("metadata") or {}) if isinstance(meta.get("metadata"), dict) else {}
    aura = aura.get("aura") if isinstance(aura, dict) else {}
    aura = aura if isinstance(aura, dict) else {}
    tags_raw = aura.get("tags") or []
    tags = tuple(str(t) for t in tags_raw) if isinstance(tags_raw, list) else ()
    groups_raw = aura.get("tool_groups") or []
    tool_groups = tuple(str(g) for g in groups_raw) if isinstance(groups_raw, list) else ()
    workflow = str(aura.get("workflow") or "")
    return Skill(
        name=name,
        description=description,
        version=version,
        body=body,
        tags=tags,
        workflow=workflow,
        tool_groups=tool_groups,
        path=path,
        when_text=_section(body, "When to use"),
    )


def parse_identity_text(text: str, *, kind: str) -> IdentityDoc:
    version = "1.0.0"
    body = text
    if text.startswith("---\n"):
        meta, body = _split_frontmatter(text)
        version = str(meta.get("version") or "1.0.0")
    return IdentityDoc(kind=kind, version=version, text=body.strip())


@cache
def list_skills() -> tuple[Skill, ...]:
    root = _package_root() / "skills"
    if not root.is_dir():
        return ()
    skills: list[Skill] = []
    for path in sorted(root.rglob("SKILL.md")):
        try:
            skill = parse_skill_text(path.read_text(encoding="utf-8"), path=path)
        except Exception:  # noqa: BLE001 — skip corrupt skills; never break the run
            logger.exception("Skipping unreadable skill at %s", path)
            continue
        skills.append(skill)
    return tuple(skills)


@cache
def load_identity() -> tuple[IdentityDoc, IdentityDoc]:
    root = _package_root()
    soul = parse_identity_text((root / "SOUL.md").read_text(encoding="utf-8"), kind="soul")
    agents = parse_identity_text((root / "AGENTS.md").read_text(encoding="utf-8"), kind="agents")
    return soul, agents


def match_skills(
    text: str,
    *,
    origin: str | None = None,
    limit: int = 2,
    skills: tuple[Skill, ...] | None = None,
) -> list[Skill]:
    """Rank skills for a user message or automation origin; return up to ``limit``."""
    catalog = list(skills) if skills is not None else list(list_skills())
    if not catalog:
        return []

    origin_l = (origin or "").lower()
    if origin_l in {"automation", "briefing"} or text.strip().lower() in {
        "daily_briefing",
        "daily briefing",
    }:
        forced = [s for s in catalog if s.name == "daily-briefing"]
        if forced:
            return forced[:limit]

    query = _tokens(text)
    scored: list[tuple[int, Skill]] = []
    for skill in catalog:
        score = 0
        name_tokens = _tokens(skill.name.replace("-", " "))
        if name_tokens & query:
            score += 5 * len(name_tokens & query)
        tag_tokens = _tokens(" ".join(skill.tags))
        score += 3 * len(tag_tokens & query)
        when_tokens = _tokens(skill.when_text)
        score += len(when_tokens & query)
        # Strong phrases for flagships
        lowered = text.lower()
        if skill.name == "remind-and-follow-up" and "remind" in lowered:
            score += 8
        if skill.name == "remember-me" and "remember" in lowered:
            score += 8
        if skill.name == "inbox-to-action" and any(
            w in lowered for w in ("reply", "email", "inbox", "gmail", "draft")
        ):
            score += 6
        if skill.name == "plan-my-time" and any(
            w in lowered for w in ("focus", "free slot", "schedule", "find time", "calendar")
        ):
            score += 6
        if skill.name == "daily-briefing" and "briefing" in lowered:
            score += 6
        if score > 0:
            scored.append((score, skill))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [s for _, s in scored[:limit]]


def clear_caches() -> None:
    list_skills.cache_clear()
    load_identity.cache_clear()
