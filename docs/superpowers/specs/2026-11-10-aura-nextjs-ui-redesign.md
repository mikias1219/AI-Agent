# AURA Next.js UI Redesign

**Date:** 2026-11-10  
**Status:** Approved in conversation; pending file review  
**Approach:** 1 — Next.js App Router UI kit + feature modules  
**Scope:** Frontend only  
**Supersedes (frontend UI only):** Vite hash-router shell and dark-violet overview mockup specs for the active UI direction. Backend/Hermes specs remain in force.

## Goal

Replace the Vite React `frontend/` with a **Next.js (App Router) + TypeScript + Tailwind** app that feels like a modern, professional, world-class personal agent. Real backend for auth and already-implemented features; mock adapters for Google, social, and not-yet-wired UI. Production CI/CD, Vercel, Render, Supabase, and shared env/secrets are **not** changed in this phase.

## Decisions locked

| Topic | Decision |
| --- | --- |
| Frontend fate | Replace `frontend/` (no parallel Vite + Next apps) |
| Production | Do not touch CI/CD, Vercel deploy config, or production env |
| Data | Real API for auth + existing features; mocks for Google/social/preview modules |
| Visual | Light professional workspace — soft canvas, charcoal type, deep teal/ink accent; no purple glass/glow |
| Navigation | Hybrid agent-first: Overview, Chat, Tasks, Activity, Connections, Settings |
| Density | One job per page; pagination for lists; modals/drawers for secondary actions |
| Duplicates | Each feature owns one route; Overview only summarizes + deep-links |
| Maintainability | Component-based: thin routes, shared shell/UI, feature modules, api vs mocks adapters |

## Architecture & boundaries

### Stack

- Next.js App Router, TypeScript, Tailwind CSS
- Python backend unchanged
- Local Next.js proxies or calls backend `/api` for real features

### Folder shape

```text
frontend/
  app/                      # routes only (thin)
    (auth)/login, register
    (app)/                  # authenticated layout
      page.tsx              # Overview
      chat, tasks, activity
      connections/...
      settings
  components/
    shell/                  # AppSidebar, AppHeader, NotificationsDrawer, ProfileMenu
    ui/                     # Button, Input, Field, Badge, Avatar, EmptyState, Modal, Drawer, Pagination
  features/
    auth/
    overview/
    chat/
    tasks/
    activity/
    connections/            # shared + telegram | google | linkedin | facebook
    settings/
  lib/
    api/                    # real backend client
    mocks/                  # mock data + adapters
    auth/                   # session helpers
    capabilities.ts         # api | mock flags per feature
  styles/                   # design tokens
```

### Rules

- Routes compose features; they do not own business UI inline.
- `components/ui` and `components/shell` have no feature imports.
- Features may use shared UI; features do not import other features’ pages.
- Same component contracts for real vs mock — swap adapter via `capabilities.ts`, not page rewrites.
- No legacy hub routes alongside new routes. One IA only.

## Information architecture (one job per page)

| Route | One job |
| --- | --- |
| `/login` | Sign in |
| `/register` | Create the single workspace owner (backend closes when owner exists) |
| `/` | Orient: greeting, compact stats, shortcuts, connection health strip — no full chat/task/connection boards |
| `/chat` | Agent conversation only |
| `/tasks` | Tasks + approvals only (paginated; approve/reject in modal) |
| `/activity` | Audit timeline only (paginated; detail in drawer) |
| `/connections` | Channel directory only (status cards → detail routes) |
| `/connections/telegram` | Operate Telegram only |
| `/connections/google` | Google apps only — one active view at a time (Gmail / Calendar / Drive via subnav or query) |
| `/connections/linkedin` | LinkedIn only |
| `/connections/facebook` | Facebook only |
| `/settings` | Account, appearance, runtime/status — section subnav, not one giant form |

Social draft preview (Content Studio) is a **modal/step on the channel page**, not a separate top-level product or Overview widget.

### Shell

- **Sidebar:** AURA brand, primary nav, Connections entry, Settings, compact user footer
- **Header:** page title, search field (UI shell only this phase), notifications bell, profile menu
- **Profile menu:** Profile (→ Settings account section), Settings, Sign out
- **Notifications:** drawer only (paginated). Items deep-link to Tasks, Activity, or Connections. No duplicate Notifications page that reimplements Activity.

### No-duplicate rules

- Approvals live on Tasks (modal), not a second Approvals app and not a full board on Overview.
- Telegram is only under Connections (plus Overview health strip link) — no separate top-level Telegram clone page.
- Content Studio is entered from the social channel context only.
- Profile is Settings → Account; header menu does not open a second profile implementation.

## Data layer

### Real API (`lib/api/`)

Login, register, logout, session, chat/history, tasks/approvals, activity/audit, Telegram lifecycle/status, `/api/status` (runtime).

### Mocks (`lib/mocks/`)

Google (Gmail/Calendar/Drive sample items), LinkedIn, Facebook, Content Studio draft samples, extra notification types for preview channels.

### Capability flags

```ts
// conceptual
{ telegram: "api", google: "mock", linkedin: "mock", facebook: "mock", chat: "api", tasks: "api", activity: "api" }
```

### Honesty

- Mock channels show **Preview** / **Integration pending** — never fake “live publishing success” as production truth.
- API down → offline banner on real features.
- Missing owner / registration closed → backend error surfaced inline on auth screens.

## Visual system

- Soft light canvas; charcoal text; one accent (deep teal or ink blue)
- Expressive display font for brand/headings; clean UI sans for controls/body
- Subtle atmosphere (quiet gradient/pattern) — not flat white void; not purple glass
- Crisp sidebar + header; content sections with purpose, not card spam
- Motion: route enter fade, notification drawer, sidebar active indicator (2–3 intentional motions)
- Responsive: usable on mobile; sidebar collapses; one column content

## Component model

### Primitives (`components/ui`)

Button, Input, Field, Textarea, Badge, Avatar, IconButton, EmptyState, Toast, Modal, Drawer, Pagination, Tabs, Spinner.

### Shell (`components/shell`)

DashboardLayout, AppSidebar, AppHeader, NotificationsDrawer, ProfileMenu.

### Feature composites (`features/*`)

Only feature-specific panels (e.g. `TelegramStatusPanel`, `ChannelGrid`, `TaskApproveModal`). No copy-paste of the same panel on Overview and detail pages — Overview uses small summary widgets that link out.

## Auth screens

- Login: email/password, validation, link to register, backend errors inline
- Register: first owner only; if registration closed, clear message + link to login
- No email password-reset flow this phase; optional note pointing to CLI recovery if needed
- After auth → Overview

## Key feature behavior

### Overview

Summary only: greeting, paginated-or-capped recent stats (counts from API), Ask agent → `/chat`, open tasks count → `/tasks`, connection health strip → detail routes. No embedded full chat thread or full task table.

### Chat / Tasks / Activity

- Chat: conversation UI against chat API when backend available
- Tasks: paginated list; approval actions in modal
- Activity: paginated timeline; row opens detail drawer
- Shared empty / loading / error patterns

### Connections

- Directory grid of channels with status
- Telegram: verify / start / stop / status / recent activity against backend
- Google: mock Gmail, Calendar, Drive — one view active; lists paginated
- Social: mock connection state; draft preview opens as a modal/step on that channel page only

### Settings

Sections via subnav: Account (profile), Appearance (tokens), Runtime (status from API when available), Permissions summary. Sign out available from profile menu and settings.

## Out of scope

- Changes to GitHub Actions, Render, Vercel production project, Supabase, or production secrets/env
- Real Google / LinkedIn / Facebook OAuth or publishing
- Email password recovery
- Backend domain redesign
- Keeping the old Vite hash-router hub as a second UI

## Success criteria

1. Register → login → shell works against backend auth.
2. Every primary feature has exactly one owning route.
3. Lists use pagination; secondary actions use modal/drawer.
4. Overview never duplicates full feature UIs.
5. Components are reusable; features are isolated; api vs mocks is explicit.
6. Production deploy path and env remain untouched.
7. UI reads as a calm, modern, professional personal agent — competitive through clarity, not widget overload.

## Implementation sequence (for planning)

1. Scaffold Next.js App Router + TypeScript + Tailwind; design tokens; UI primitives.
2. Auth routes + session against backend.
3. Dashboard shell (sidebar, header, notifications drawer, profile menu).
4. Overview (summary widgets only).
5. Chat, Tasks (modal approvals), Activity (drawer + pagination).
6. Connections directory + Telegram (API) + Google/Social (mocks).
7. Settings sections.
8. Polish empty/loading/error + motion; local run docs only (no production CI edits).
