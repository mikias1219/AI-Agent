"""Unit tests for agent skill loader and compose (offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_agent.agent.compose import compose_procedures
from personal_agent.agent.loader import (
    clear_caches,
    match_skills,
    parse_identity_text,
    parse_skill_text,
)

FIXTURE_SKILL = """---
name: remind-and-follow-up
description: Create a durable reminder at a resolved local time for the owner.
version: 1.0.0
metadata:
  aura:
    workflow: W4
    tags: [remind, reminder]
---

# Remind

## When to use

When the owner asks to be reminded.

## Procedure

1. Call `reminder_create`.

## Stop conditions

- Ambiguous time.

## Never

- Invent ids.

## Verification

| Field | Source |
| --- | --- |
| `reminder_id` | tool |
"""


def test_parse_skill_frontmatter():
    skill = parse_skill_text(FIXTURE_SKILL)
    assert skill.name == "remind-and-follow-up"
    assert skill.version == "1.0.0"
    assert "remind" in skill.tags
    assert "reminded" in skill.when_text.lower() or "remind" in skill.when_text.lower()


def test_match_remind_phrase():
    skill = parse_skill_text(FIXTURE_SKILL)
    matched = match_skills(
        "Remind me tomorrow at 9 to call the bank",
        skills=(skill,),
    )
    assert [s.name for s in matched] == ["remind-and-follow-up"]


def test_match_briefing_origin_forces_daily_briefing():
    briefing = parse_skill_text(
        FIXTURE_SKILL.replace("remind-and-follow-up", "daily-briefing")
        .replace("W4", "W1")
        .replace("Remind", "Briefing")
    )
    other = parse_skill_text(FIXTURE_SKILL)
    # Fix name in parsed briefing — replace only changed the string once for name line
    briefing = parse_skill_text(
        """---
name: daily-briefing
description: Build today's briefing from calendar and tasks without inventing data.
version: 1.0.0
metadata:
  aura:
    workflow: W1
    tags: [briefing]
---

# Briefing

## When to use

Morning briefing.

## Procedure

1. Call `task_list`.

## Stop conditions

- None.

## Never

- Invent meetings.

## Verification

| Field | Source |
| --- | --- |
| `outcome` | run |
"""
    )
    matched = match_skills("daily_briefing", origin="automation", skills=(briefing, other))
    assert [s.name for s in matched] == ["daily-briefing"]


def test_compose_version_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    clear_caches()
    soul = parse_identity_text("---\nversion: 1.2.3\n---\n\n# Soul\n\nHello.\n", kind="soul")
    agents = parse_identity_text(
        "---\nversion: 1.0.0\n---\n\n# Agents\n\n## Run end states\n\nDone.\n",
        kind="agents",
    )
    skill = parse_skill_text(FIXTURE_SKILL)
    composed = compose_procedures(
        "Remind me tomorrow",
        identity=(soul, agents),
        skills=(skill,),
    )
    assert "Remind" in composed.text or "reminder" in composed.text.lower()
    assert composed.version_suffix == "+soul@1.2.3+skills:remind-and-follow-up@1.0.0"


def test_corrupt_skill_skipped_by_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from personal_agent.agent import loader as loader_mod

    clear_caches()
    skills_dir = tmp_path / "skills" / "broken"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("not valid", encoding="utf-8")
    good_dir = tmp_path / "skills" / "remind-and-follow-up"
    good_dir.mkdir(parents=True)
    (good_dir / "SKILL.md").write_text(FIXTURE_SKILL, encoding="utf-8")

    monkeypatch.setattr(loader_mod, "_package_root", lambda: tmp_path)
    clear_caches()
    skills = loader_mod.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "remind-and-follow-up"
    clear_caches()
