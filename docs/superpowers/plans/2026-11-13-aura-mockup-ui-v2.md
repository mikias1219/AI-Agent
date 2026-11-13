# AURA Mockup UI v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or implement inline task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Full product UI parity with the updated 30-frame mockup (Approach 2).

**Architecture:** Frontend-first on `feature/aura-mockup-ui-v2`. Reuse existing APIs. Persist theme preference locally (and profile JSON if cheap). Bell reads inbox + activity. Density preference localStorage.

**Tech Stack:** Next.js App Router, Tailwind + CSS vars, existing FastAPI contracts.

**Spec:** `docs/superpowers/specs/2026-11-13-aura-mockup-ui-v2-design.md`

## Global Constraints

- No invented calendar/email/task facts
- Cards from `result_type` only
- Accent never for status; warning never for errors
- Hard ceilings / pause / quiet hours unchanged
- Conventional commits; do not commit secrets or the xlsx

---

### Task 0: Branch, tokens, dark theme, density atoms

- [x] Create `feature/aura-mockup-ui-v2` from main; commit spec+plan
- [x] Extend `frontend/styles/tokens.css` with dark theme (`html[data-theme="dark"]`)
- [x] Add `DensityProvider` / localStorage `aura-density` comfortable|compact
- [x] Ensure StatusChip / CompactRow respect density; commit `feat(ui): dark tokens and density atoms`

### Task 1: Shell — listening, bell, menus, remove Help rail

- [x] Sidebar: Agent listening/Paused from agent-control
- [x] Header: “Ask or tell AURA…”, autonomy popover, restore Bell drawer (Needs you + Updates)
- [x] Remove permanent HelpPanel from `dashboard-layout`
- [x] Commit `feat(shell): bell drawer, listening status, drop help rail`

### Task 2: Today density + mobile polish

- [x] Comfortable/Compact toggle on Today; compact row metrics
- [x] Mobile-friendly section stacking
- [x] Commit `feat(today): comfortable/compact density`

### Task 3: Chat + Inbox visual parity

- [x] Align Chat thread/composer chrome with mockup
- [x] Inbox Needs you/Done copy and row density
- [x] Commit `feat(chat-inbox): mockup visual parity`

### Task 4: Tasks board + Memory Proposed

- [x] Tasks List|Board toggle (board = columns by status/view)
- [x] Memory tab Proposed (memory proposals / empty honest)
- [x] Commit `feat(tasks-memory): board view and proposed tab`

### Task 5: Mail buckets + Calendar chrome

- [x] Mail buckets client-side; Calendar Today/Week/Day + Find time → quick-ask
- [x] Commit `feat(google-ui): mail buckets and calendar chrome`

### Task 6: Appearance + 4-step wizard

- [x] Settings Appearance Light/Dark/System
- [x] First-run Profile → Model → Connect → Autonomy
- [x] Commit `feat(settings): appearance theme and four-step wizard`

### Task 7: Help W1–W6 + polish Connections/Activity/Routines

- [x] Help page loop + six workflows
- [x] Activity pagination polish; Connections/Routines copy
- [x] Commit `feat(help): workflows and surface polish`

### Task 8: Tests + ADR + status

- [x] Playwright shell/bell/density/theme smoke
- [x] ADR appearance/dark; mark spec Implemented
- [x] Commit `docs: UI v2 ADR and status`
