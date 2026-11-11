# P1 Task Model Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans. Checkboxes for tracking.

**Goal:** Extend tasks with TSK-01 fields, owner_profile, date resolution, tools, API views, and Tasks UI.

**Architecture:** Domain Task + OwnerProfile; Alembic migration; TaskService + tools; FastAPI routes; Tasks page views/drawer.

**Tech Stack:** Existing FastAPI/SQLAlchemy/Alembic, Next.js Tasks UI

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-11-aura-phase1-p1-task-model-design.md`
- Proposal P1 prompt; BR-06 transitions already done in P0
- Soft delete = destructive tool class; never hard-delete in v1
- Offline pytest; no secrets
- Do not implement P2–P8 in this plan

---

### Task 1: Domain + migration

- [ ] Extend `Task` dataclass and ORM with: priority (optional str enum), due_at (tz-aware datetime nullable), project (str), tags (JSON list), source, source_ref, completed_at, deleted_at (soft delete)
- [ ] Add `OwnerProfile` model + table (owner_id PK, timezone default UTC, language default en)
- [ ] Alembic migration SQLite+Postgres safe
- [ ] Unit tests for model defaults
- [ ] Commit `feat(tasks): extend Task and OwnerProfile schema`

### Task 2: Date resolution + TaskService

- [ ] `resolve_relative_date(text, timezone, now=)` helper — Friday, tomorrow, 3pm patterns; DST/month-end tests
- [ ] TaskService: create/update/search/reopen/soft_delete; list with view filters; exclude deleted by default
- [ ] completed_at set on →done; cleared on reopen
- [ ] Commit `feat(tasks): service search, views, and date resolution`

### Task 3: Tools + API

- [ ] Update builtins/tasks.py tools + register delete as destructive
- [ ] Extend `/api/tasks` query params and payloads; profile GET/PATCH minimal endpoints if needed for timezone
- [ ] Integration tests for views/filters
- [ ] Commit `feat(tasks): API views and task tools`

### Task 4: Tasks UI

- [ ] Views Today/Upcoming/Overdue/All/Done; quick add; priority/due badges; detail drawer; empty/error
- [ ] Vitest for any pure filter helpers
- [ ] Commit `feat(ui): Tasks views, quick add, and detail drawer`

### Task 5: Verify

- [ ] Full pytest + frontend tsc/test/format
- [ ] Mark P1 spec Implemented
- [ ] Commit; controller merges/deploys

---

## After this plan

Controller continues without re-asking scope: **P2 AgentRun** → **P3 durable approvals** → **P4 memory** → **P5 Today** → **P6 scheduler** → **P7 Google** → **P8 Telegram** (per `docs/AURA_PROPOSAL.md`).
