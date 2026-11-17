"""Static checks on shipped SOUL / AGENTS / SKILL.md files."""

from __future__ import annotations

import re

import pytest

from personal_agent.agent.loader import (
    clear_caches,
    list_skills,
    load_identity,
    parse_skill_text,
)

REQUIRED_SECTIONS = (
    "## When to use",
    "## Procedure",
    "## Stop conditions",
    "## Never",
    "## Verification",
)

# Built-in tool names skills may reference (keep in sync with builtins).
KNOWN_TOOLS = frozenset(
    {
        "google_gmail_list",
        "google_gmail_search",
        "google_gmail_read",
        "google_gmail_create_draft",
        "google_gmail_send",
        "google_gmail_reply",
        "google_create_task_from_email",
        "google_calendar_list",
        "google_calendar_find_free_slots",
        "google_calendar_create",
        "google_calendar_update",
        "google_calendar_delete_event",
        "task_create",
        "task_list",
        "task_search",
        "task_update",
        "task_update_status",
        "task_reopen",
        "reminder_create",
        "reminder_list",
        "reminder_cancel",
        "memory_save",
        "memory_search",
        "memory_forget",
        "memory_forget_all",
        "web_search",
        "web_fetch",
    }
)

TOOL_REF = re.compile(r"`([a-z][a-z0-9_]*)`")
TOOL_PREFIXES = ("google_", "task_", "reminder_", "memory_", "web_")
FILE_REF = re.compile(r"`((?:templates|references)/[^`\s]+)`")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


@pytest.fixture(autouse=True)
def _clear():
    clear_caches()
    yield
    clear_caches()


def test_identity_files_load():
    soul, agents = load_identity()
    assert soul.version
    assert "Never" in soul.text or "never" in soul.text.lower()
    assert agents.version
    assert "Done" in agents.text or "end" in agents.text.lower()


def test_there_are_five_flagship_skills():
    names = {s.name for s in list_skills()}
    assert names == {
        "daily-briefing",
        "inbox-to-action",
        "plan-my-time",
        "remind-and-follow-up",
        "remember-me",
    }


@pytest.mark.parametrize("skill", list_skills(), ids=lambda s: s.name)
def test_frontmatter(skill):
    assert skill.path is not None
    assert skill.name == skill.path.parent.name
    assert len(skill.description) >= 30
    assert SEMVER.fullmatch(skill.version)


@pytest.mark.parametrize("skill", list_skills(), ids=lambda s: s.name)
def test_required_sections(skill):
    assert skill.path is not None
    text = skill.path.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    assert not missing, f"{skill.name} missing {missing}"
    parse_skill_text(text, path=skill.path)


@pytest.mark.parametrize("skill", list_skills(), ids=lambda s: s.name)
def test_tools_are_known(skill):
    assert skill.path is not None
    text = skill.path.read_text(encoding="utf-8")
    used = {
        m for m in TOOL_REF.findall(text) if any(m.startswith(prefix) for prefix in TOOL_PREFIXES)
    }
    assert used, f"{skill.name} should name at least one tool"
    unknown = used - KNOWN_TOOLS
    assert not unknown, f"{skill.name} unknown tools: {unknown}"


@pytest.mark.parametrize("skill", list_skills(), ids=lambda s: s.name)
def test_referenced_files_exist(skill):
    assert skill.path is not None
    text = skill.path.read_text(encoding="utf-8")
    for relative in FILE_REF.findall(text):
        assert (skill.path.parent / relative).is_file(), relative
