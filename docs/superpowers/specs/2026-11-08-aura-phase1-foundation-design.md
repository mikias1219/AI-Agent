# AURA Phase 1 — Product Foundation Design

**Date:** 2026-11-08  
**Status:** Draft for review  
**Approach:** A — Shell + design only (JSX, existing hash routing, no stack migration)

## Goal

Evolve the existing React dashboard into an AURA-shaped product shell: dark-navy design system, persistent module navigation, Overview driven only by real API data, and honest unavailable/offline states for capabilities not built yet (local worker, calendar, context graph, etc.).

Phase 1 does **not** change Hermes, Ollama, OpenRouter, job queues, Supabase Auth/RLS, or backend domain models.

## Decisions locked

| Topic | Decision |
| --- | --- |
| Delivery approach | A — shell + design only |
| Telegram nav | **Top-level sidebar item** (best for current UX and Playwright coverage). Unified Inbox is a placeholder that links to Telegram as the first connected channel. |
| Approvals | Remain on Tasks & Goals page (no new Approvals route/API in Phase 1) |
| Branding | Rename UI to **AURA** |
| Auth | Keep existing cookie owner auth |
| Stack | Stay on JSX + hash router + current polling hooks |
| Backend | No new endpoints |

## Information architecture

Hash routes remain (`#today`, `#agent`, …).

### Sidebar sections

**Overview**

| Route | Label | Phase 1 behavior |
| --- | --- | --- |
| `#today` | Overview | Redesigned home from real API data |

**Assist**

| Route | Label | Phase 1 behavior |
| --- | --- | --- |
| `#agent` | My Agent | Existing chat, restyled |
| `#telegram` | Telegram | Existing Telegram controls, restyled |
| `#inbox` | Unified Inbox | Placeholder; CTA to open `#telegram` |

**Plan**

| Route | Label | Phase 1 behavior |
| --- | --- | --- |
| `#tasks` | Tasks & Goals | Existing tasks + approvals; Goals marked “Coming later” |
| `#calendar` | Calendar | Placeholder empty state |
| `#growth` | Personal Growth | Placeholder empty state |
| `#automation` | Automation Studio | Placeholder (replaces Content Studio in nav) |

**Knowledge**

| Route | Label | Phase 1 behavior |
| --- | --- | --- |
| `#memory` | Memory | Placeholder empty state |
| `#knowledge` | Knowledge Hub | Placeholder empty state |

**System**

| Route | Label | Phase 1 behavior |
| --- | --- | --- |
| `#connections` | Integrations | Existing connections page, restyled |
| `#activity` | Activity & Logs | Existing activity, restyled |
| `#settings` | Settings | Lightweight page: profile from `/api/auth`; worker/privacy controls labeled unavailable |

### Legacy routes

- `#studio` (Content Studio): remove from nav. If visited, show Automation Studio placeholder (same component) or redirect to `#automation`.
- Auth routes unchanged: `#login`, `#register`, `#reset`.

## Visual system

- Foundation: dark navy surfaces (approx. `#0B1220` background, elevated `#111827` / `#1A2332` panels).
- Accents: subtle violet/blue (not light purple-on-white).
- Typography: Inter loaded from a free font source in `index.html`.
- Tokens in `frontend/src/shared/styles/globals.css`: background, surface, border, muted, accent, danger, success.
- Restyle shared utilities: `.card`, `.primary`, `.secondary`, `.field`, `.label`, `.eyebrow`.
- Brand: **AURA** wordmark + mark in `Brand.jsx`.
- Document title pattern: `{Page} · AURA`.
- Sidebar footer status strip (real data only):
  - Provider (`status.provider`)
  - Model (`status.model`)
  - Worker: always **Not connected yet** in Phase 1 (honest; worker ships later)
  - Telegram: derived from `status.telegram` (configured / managed / listening when available)

Accessible focus states and contrast must remain usable on dark surfaces.

## Overview (Home) data rules

Use only real fields from existing workspace polling (`/api/status`, `/api/tasks`, `/api/approvals`, `/api/activity`):

- Priority / open tasks from `/api/tasks` (non-terminal statuses, capped list).
- Pending approvals count from actionable `/api/approvals` items.
- Recent activity: last N events from `/api/activity`.
- Agent status: provider + model from `/api/status`.
- Ask bar: unchanged behavior — submits into My Agent chat.

Explicit unavailable blocks (not fake zeros):

- Upcoming events
- Active projects / goals progress
- Local worker online/offline beyond “Not connected yet”
- Calendar summary

## Components and structure

**Preserve**

- `useWorkspaceData` polling
- `useAgentChat` streaming
- `shared/api/client.js` cookie auth
- Feature folders under `frontend/src/features/`

**Add (small, shared)**

- `EmptyState` — title + one sentence for placeholders
- `ModulePlaceholder` — standard “Not available yet” page shell
- `StatusPill` — compact status chip for sidebar/overview

**Pages**

- Restyle: auth, Overview/home, chat, telegram, tasks, connections, activity
- New placeholders: inbox, calendar, memory, knowledge, growth, automation, settings
- Settings shows real profile name/email when present; all worker/export/deletion controls marked unavailable

No Redux/Zustand/TanStack Query in Phase 1.

## Error and loading behavior

- Keep existing boot error and workspace refresh error banners (restyled for dark theme).
- Placeholder modules do not call new APIs.
- Overview sections that lack data show empty states (“No open tasks”) vs unavailable (“Coming in a later phase”) distinctly.

## Testing

- Update `frontend/tests/e2e/workspace.spec.js` for AURA labels, new nav, and Overview copy as needed.
- Acceptance commands:
  - `npm --prefix frontend run build`
  - `npm --prefix frontend run format:check`
  - `npm --prefix frontend run test:e2e`
- Backend pytest unchanged unless a frontend-only change accidentally requires it (not expected).

## Documentation

- This spec is the Phase 1 design record.
- After implementation, add a short note to `docs/architecture.md` describing the AURA shell IA and that the local worker is not connected yet.

## Out of scope

- TypeScript, shadcn, React Router, React Hook Form, Zod, TanStack Query
- Hermes / Ollama / OpenRouter changes
- Local worker, job queue, leases
- Supabase Auth, RLS, Storage, pgvector
- Goals/projects/calendar/memory/knowledge domain APIs
- Fake online worker or simulated AI metrics

## Acceptance criteria

1. Desktop persistent sidebar with grouped AURA modules; mobile drawer preserved.
2. Dark navy foundation; AURA brand visible in shell and auth.
3. Telegram remains a top-level nav item; Inbox placeholder links to it.
4. Overview metrics come from real APIs or are explicitly marked unavailable.
5. Worker shown as **Not connected yet**; no fake online state.
6. Existing chat, tasks, approvals, Telegram, auth, and activity still work.
7. No fake charts or hardcoded activity counts.
8. Frontend build, format check, and Playwright e2e pass.

## Implementation notes (for the following plan)

Primary touch points:

- `frontend/index.html`
- `frontend/src/shared/styles/globals.css`
- `frontend/src/shared/components/ui/*`
- `frontend/src/app/layouts/DashboardLayout.jsx`
- `frontend/src/app/routing/navigation.js`
- `frontend/src/app/App.jsx`
- `frontend/src/features/home/pages/HomePage.jsx`
- New feature placeholder pages under `frontend/src/features/`
- `frontend/tests/e2e/workspace.spec.js`
- `docs/architecture.md` (brief post-implement update)
