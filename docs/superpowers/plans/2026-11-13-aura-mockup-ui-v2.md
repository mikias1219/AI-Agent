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

- [ ] Create `feature/aura-mockup-ui-v2` from main; commit spec+plan
- [ ] Extend `frontend/styles/tokens.css` with dark theme (`html[data-theme="dark"]`)
- [ ] Add `DensityProvider` / localStorage `aura-density` comfortable|compact
- [ ] Ensure StatusChip / CompactRow respect density; commit `feat(ui): dark tokens and density atoms`

### Task 1: Shell — listening, bell, menus, remove Help rail

- [ ] Sidebar: Agent listening/Paused from agent-control
- [ ] Header: “Ask or tell AURA…”, autonomy popover, restore Bell drawer (Needs you + Updates)
- [ ] Remove permanent HelpPanel from `dashboard-layout`
- [ ] Commit `feat(shell): bell drawer, listening status, drop help rail`

### Task 2: Today density + mobile polish

- [ ] Comfortable/Compact toggle on Today; compact row metrics
- [ ] Mobile-friendly section stacking
- [ ] Commit `feat(today): comfortable/compact density`

### Task 3: Chat + Inbox visual parity

- [ ] Align Chat thread/composer chrome with mockup
- [ ] Inbox Needs you/Done copy and row density
- [ ] Commit `feat(chat-inbox): mockup visual parity`

### Task 4: Tasks board + Memory Proposed

- [ ] Tasks List|Board toggle (board = columns by status/view)
- [ ] Memory tab Proposed (memory proposals / empty honest)
- [ ] Commit `feat(tasks-memory): board view and proposed tab`

### Task 5: Mail buckets + Calendar chrome

- [ ] Mail buckets client-side; Calendar Today/Week/Day + Find time → quick-ask
- [ ] Commit `feat(google-ui): mail buckets and calendar chrome`

### Task 6: Appearance + 4-step wizard

- [ ] Settings Appearance Light/Dark/System
- [ ] First-run Profile → Model → Connect → Autonomy
- [ ] Commit `feat(settings): appearance theme and four-step wizard`

### Task 7: Help W1–W6 + polish Connections/Activity/Routines

- [ ] Help page loop + six workflows
- [ ] Activity pagination polish; Connections/Routines copy
- [ ] Commit `feat(help): workflows and surface polish`

### Task 8: Tests + ADR + status

- [ ] Playwright shell/bell/density/theme smoke
- [ ] ADR appearance/dark; mark spec Implemented
- [ ] Commit `docs: UI v2 ADR and status`
