# AURA Phase 0 — Truth and Foundation

**Date:** 2026-11-11  
**Status:** Approved — awaiting implementation plan  
**Source of truth:** `docs/AURA Personal AI Agent — Product Proposal and Functional Requirements.md` (Part 2 FND-\*, TSK-02; Part 3 prompt P0)  
**Roadmap mode:** Sequential full proposal (Approach 1); this is the first slice only

## Goal

Make the repository an honest AURA foundation: one product identity, docs that match code, no mock social/Hub surfaces, correct task transitions, Cursor rules, and a minimal automated test/CI baseline — before Phase 1 trust/memory/Today work.

## Decisions locked

| Topic | Decision |
| --- | --- |
| Product name | **AURA** in UI, package metadata, and deploy docs |
| Hub / Product-Mgt | Remove now; ADR records “reuse later as Playbooks” |
| LinkedIn / Facebook | Remove from navigation, routes, mocks, capabilities for v1.0 |
| Task transitions | BR-06 / TSK-02 matrix (planned→done; reopen done/cancelled→planned) |
| Proposal pointer | Commit/copy as `docs/AURA_PROPOSAL.md` for Cursor `@` references |
| Later phases | Not in this slice (AgentRun, durable approvals, memory, Today, scheduler, MCP, U0–U5 redesign) |

## Requirements in scope

| ID | Summary |
| --- | --- |
| FND-01 | One name AURA; no “Personal Agent Hub”, “Product-Mgt”, or local machine paths in live docs |
| FND-02 | README, architecture, deploy, frontend README match Next.js + Google + Telegram; feature-status from `capabilities.ts` + CI check |
| FND-03 | Remove LinkedIn/Facebook UI + mocks; remove `/api/hub/state` + `HubStore` (+ migration if tables exist); delete `docs/references/product-mgt.md`; ADR |
| FND-04 | Vitest for UI logic; Playwright smoke (register, login, fake chat, create task, approve); both in CI |
| FND-05 | Start `docs/adr/` (at least remove-hub-mocks ADR; note single-owner deferred if needed) |
| FND-06 | `.cursor/rules/aura-core.mdc`, `aura-frontend.mdc`, root `AGENTS.md` (from proposal Part 3) |
| FND-07 | import-linter + mypy on `domain` and `application` in CI; fix real violations found |
| TSK-02 | Transition matrix per proposal; unit test every status pair |

## Task transition matrix (TSK-02)

Replace current rules that block planned→done and reopen.

| From | Allowed to |
| --- | --- |
| planned | in_progress, done, cancelled |
| in_progress | planned, blocked, done, cancelled |
| blocked | planned, in_progress, cancelled |
| done | planned |
| cancelled | planned |

Illegal moves return a friendly domain error (existing pattern).

## Removals (FND-03)

**Frontend**

- Routes/pages: `/connections/linkedin`, `/connections/facebook`
- Nav / Overview / health / channel-grid entries for LinkedIn and Facebook
- `capabilities.linkedin` / `capabilities.facebook` (or mark absent and unused)
- Mock modules used only by those pages (`lib/mocks/social.ts` usage, preview notifications)

**Backend**

- `GET`/`PUT` `/api/hub/state`
- `HubStore` and container wiring
- Hub-related tests
- Alembic migration to drop hub tables if present

**Docs**

- Delete `docs/references/product-mgt.md`
- Scrub Hub / Product-Mgt / stale Vite claims from README, architecture, deploy, frontend README

## Docs and status table (FND-02)

- Rewrite docs to describe: FastAPI + Next.js 15, Telegram always-on, Google OAuth live, Render/Vercel/Supabase, tool gate
- Script (e.g. `scripts/check-feature-status.mjs` or Python) reads `frontend/lib/capabilities.ts` and fails CI if a feature marked `mock` is advertised as available in a checked status markdown/table — or generate the table into README from capabilities
- Prefer: generate a `docs/feature-status.md` (or README section) from capabilities and CI diff/check

## Cursor setup (FND-06)

Create exactly as in the proposal Part 3:

- `.cursor/rules/aura-core.mdc` (alwaysApply)
- `.cursor/rules/aura-frontend.mdc` (globs frontend)
- `AGENTS.md` at repo root
- `docs/AURA_PROPOSAL.md` — same content as the Product Proposal file (copy or symlink-safe duplicate for stable `@docs/AURA_PROPOSAL.md`)

## Tests and CI (FND-04, FND-07)

**Backend**

- Update `backend/tests/unit/test_task_service.py` (and any transition tests) for the new matrix; add exhaustive pair coverage
- Keep offline pytest suite green
- Add mypy on `domain` + `application`; import-linter contracts; wire into GitHub Actions

**Frontend**

- Add Vitest + at least one unit test (e.g. Telegram agent-state mapper or a pure helper)
- Add Playwright smoke: register → login → chat with fake provider → create task → approve (stub/fake as needed for CI)
- `package.json` scripts: `test`, `test:e2e`
- CI: run format, tsc, vitest, playwright smoke (with fake provider / test env)

## Out of scope

- P1–P8 features (task fields expansion beyond transitions, AgentRun, durable approvals, memory, Today shell, automations, MCP, Google tool expansion, Telegram gate rewrite)
- Part 4 design-system visual overhaul (U0–U5)
- Demo mode (`UX-12`)
- Changing reply-gate policy

## Success criteria

1. CI green on main-bound PR/push including new checks that are in scope
2. Repo search finds no Product-Mgt / Agent Hub / LinkedIn-Facebook mock routes in live app code
3. `planned → done` and `done → planned` work via API/domain tests
4. Cursor rules + `AGENTS.md` + `docs/AURA_PROPOSAL.md` present
5. No new mock data surfaces in normal mode

## Spec self-review

- Scoped to Phase 0 IDs only; later phases explicitly deferred
- TSK-02 matrix copied from proposal BR-06
- Removals and CI additions are concrete enough to plan without TBD product choices
