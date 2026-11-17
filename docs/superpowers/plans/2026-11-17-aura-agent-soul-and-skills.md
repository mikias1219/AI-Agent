# AURA agent SOUL and skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a git-gated SOUL + agent AGENTS + five W1–W5 SKILL.md procedures, load them into chat/briefing prompts, and lock the shape with offline tests.

**Architecture:** New `personal_agent.agent` package holds markdown identity/skills and a pure loader/composer. `ChatService._system_message` and briefing prompt versioning append matched procedures. ToolRegistry unchanged; skills only name built-in tool ids.

**Tech Stack:** Python 3, PyYAML (already in backend if present — else stdlib frontmatter split), pytest, existing prompts package.

## Global Constraints

- Layers: `agent/` imports nothing from application/infrastructure.
- Tool ids in skills must match registry names (`google_gmail_search`, etc.).
- Max 2 skills injected per turn; briefing always loads `daily-briefing`.
- Do not change ToolRegistry / hard ceilings / pause.
- Root `AGENTS.md` stays CI/dev; agent ops live in `agent/AGENTS.md`.
- Spec: `docs/superpowers/specs/2026-11-17-aura-agent-soul-and-skills-design.md`.

---

### Task 1: Loader + compose unit tests and package

**Files:**
- Create: `backend/src/personal_agent/agent/__init__.py`
- Create: `backend/src/personal_agent/agent/loader.py`
- Create: `backend/src/personal_agent/agent/compose.py`
- Create: `backend/tests/unit/test_agent_skills_loader.py`

**Interfaces:**
- Produces: `list_skills()`, `match_skills(text, *, origin=None, limit=2) -> list[Skill]`, `compose_procedure_block(...) -> tuple[str, str]` (body, version_suffix)

- [x] **Step 1:** Write failing tests for parse, match (remind + briefing origin), version suffix, skip corrupt skill.
- [x] **Step 2:** Implement loader (minimal YAML frontmatter, no PyYAML) and compose.
- [x] **Step 3:** `pytest backend/tests/unit/test_agent_skills_loader.py -v` PASS.

---

### Task 2: SOUL, AGENTS, five W1–W5 skills

**Files:**
- Create: `backend/src/personal_agent/agent/SOUL.md`
- Create: `backend/src/personal_agent/agent/AGENTS.md`
- Create: `backend/src/personal_agent/agent/skills/*/SKILL.md` (five)
- Create: `backend/tests/unit/test_agent_skill_files.py`

**Interfaces:**
- Consumes: loader from Task 1
- Produces: on-disk skills with real tool names

- [x] **Step 1:** Write static skill-file tests (frontmatter, sections, known tools allowlist, refs).
- [x] **Step 2:** Author SOUL, AGENTS, five skills with correct tool ids.
- [x] **Step 3:** Tests PASS.

**Built-in allowlist (minimum for skills):**  
`google_gmail_list`, `google_gmail_search`, `google_gmail_read`, `google_gmail_create_draft`, `google_gmail_send`, `google_gmail_reply`, `google_create_task_from_email`, `google_calendar_list`, `google_calendar_find_free_slots`, `google_calendar_create`, `task_create`, `task_list`, `reminder_create`, `reminder_list`, `reminder_cancel`, `memory_save`, `memory_search`, `memory_forget`, `approval`-related none — approvals are product UX not tools.

---

### Task 3: Wire into ChatService and briefing

**Files:**
- Modify: `backend/src/personal_agent/application/services/chat_service.py` (`_system_message`, prepare_turn to pass user text for match)
- Modify: `backend/src/personal_agent/application/services/briefing_builder.py` (prompt_version includes soul + daily-briefing)
- Modify: `backend/src/personal_agent/prompts/__init__.py` if helpful helpers for version join
- Test: `backend/tests/unit/test_agent_runs.py` or new `test_chat_procedure_prompt.py`

- [x] **Step 1:** Failing test: prepare/system message for “Remind me tomorrow…” includes `remind-and-follow-up` and version fragment.
- [x] **Step 2:** Wire compose into `_system_message(identity, facts=..., user_text=..., origin=...)`.
- [x] **Step 3:** Briefing sets origin automation → always daily-briefing in version.
- [x] **Step 4:** Tests PASS; durable approval suite still green sample.

---

### Task 4: ADR + README + spec status

**Files:**
- Create: `docs/adr/0023-agent-soul-and-skills.md`
- Modify: `README.md` (short bullet under features)
- Modify: `docs/superpowers/specs/2026-11-17-aura-agent-soul-and-skills-design.md` status → Implemented

- [x] **Step 1:** Write ADR.
- [x] **Step 2:** README bullet; update spec status.
- [x] **Step 3:** `ruff check` on touched Python; `pytest` unit tests for agent skills + chat procedure.
