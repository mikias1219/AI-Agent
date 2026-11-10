# AURA Next.js UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `frontend/` with a Next.js App Router TypeScript app: light professional AURA shell, one-job-per-page routes, real backend auth/chat/tasks/activity/Telegram, and mock Google/social — without touching production CI/CD or Vercel config.

**Architecture:** Thin App Router pages compose feature modules. Shared shell (`components/shell`) and primitives (`components/ui`) stay feature-agnostic. `lib/api` talks to the Python backend with cookie credentials; `lib/mocks` + `lib/capabilities.ts` supply preview data for unwired channels. Lists paginate; secondary actions use Modal/Drawer.

**Tech Stack:** Next.js 15 App Router, React 19, TypeScript, Tailwind CSS 4, lucide-react, next/font (display + UI sans). Node ≥ 22.12.

## Global Constraints

- Do **not** modify `.github/workflows/*`, `vercel.json`, `render.yaml`, or production env/secrets docs.
- Do **not** invent live health for mock channels — label **Preview** / **Integration pending**.
- One owning route per feature; Overview only summarizes + deep-links.
- Pagination for lists; modals/drawers for secondary actions — no feature duplication across pages.
- Cookie session name remains `personal_agent_session`; `credentials: "include"` on all API calls.
- Backend base URL via `NEXT_PUBLIC_API_BASE_URL` (empty = same-origin `/api` through Next rewrites in `next.config.ts` for local dev).
- Replace Vite app in place under `frontend/`; remove obsolete Vite entry files as Next scaffold lands.
- CI/Vercel cutover is **out of scope**; verify locally with `npm run dev` / `npm run build`. Do not push breaking frontend to `main` until a separate cutover is approved.

---

## File structure (create)

```text
frontend/
  package.json                          # next, react, tailwind, typescript scripts
  tsconfig.json
  next.config.ts                        # rewrite /api → backend in dev
  postcss.config.mjs
  next-env.d.ts
  .env.local.example                    # NEXT_PUBLIC_API_BASE_URL=
  app/
    layout.tsx                          # root fonts + tokens
    globals.css
    (auth)/
      layout.tsx
      login/page.tsx
      register/page.tsx
    (app)/
      layout.tsx                        # DashboardLayout + auth gate
      page.tsx                          # Overview
      chat/page.tsx
      tasks/page.tsx
      activity/page.tsx
      connections/page.tsx
      connections/telegram/page.tsx
      connections/google/page.tsx
      connections/linkedin/page.tsx
      connections/facebook/page.tsx
      settings/page.tsx
  components/ui/
    button.tsx, input.tsx, field.tsx, textarea.tsx
    badge.tsx, avatar.tsx, icon-button.tsx
    empty-state.tsx, toast.tsx, modal.tsx, drawer.tsx
    pagination.tsx, tabs.tsx, spinner.tsx
  components/shell/
    dashboard-layout.tsx
    app-sidebar.tsx
    app-header.tsx
    notifications-drawer.tsx
    profile-menu.tsx
  features/auth/
    login-form.tsx, register-form.tsx, use-auth.ts
  features/overview/
    overview-page.tsx, summary-stats.tsx, health-strip.tsx
  features/chat/
    chat-page.tsx, message-list.tsx, composer.tsx, use-chat.ts
  features/tasks/
    tasks-page.tsx, task-list.tsx, task-approve-modal.tsx, use-tasks.ts
  features/activity/
    activity-page.tsx, activity-list.tsx, activity-detail-drawer.tsx, use-activity.ts
  features/connections/
    channel-grid.tsx, channel-card.tsx
    telegram/telegram-page.tsx, telegram-status-panel.tsx, use-telegram.ts
    google/google-page.tsx, google-subnav.tsx
    social/social-channel-page.tsx, draft-preview-modal.tsx
  features/settings/
    settings-page.tsx, settings-subnav.tsx
    account-section.tsx, appearance-section.tsx, runtime-section.tsx
  lib/
    capabilities.ts
    api/client.ts, auth.ts, chat.ts, tasks.ts, activity.ts, telegram.ts, status.ts, types.ts
    mocks/google.ts, social.ts, notifications.ts
    auth/session.ts
    pagination.ts
  styles/tokens.css
```

**Delete when superseded:** Vite `index.html`, `vite.config.js`, `src/main.jsx`, old `src/app/**`, old `src/features/**`, old `src/shared/**` (after Next routes work). Keep Playwright e2e only if updated in a later task; otherwise leave `tests/` untouched until a follow-up (do not break plan scope chasing e2e).

---

### Task 1: Scaffold Next.js + tokens + UI primitives

**Files:**
- Create: all of `frontend/package.json`, `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`, `app/layout.tsx`, `app/globals.css`, `styles/tokens.css`, and every file under `components/ui/`
- Delete: `frontend/vite.config.js`, `frontend/index.html` (after Next `dev` works)

**Interfaces:**
- Produces: UI primitives with these exports:
  - `Button({ variant?: "primary" | "secondary" | "ghost" | "danger"; size?: "sm" | "md"; loading?: boolean; ...props })`
  - `Input`, `Textarea`, `Field({ label, error, children })`
  - `Badge({ tone?: "neutral" | "accent" | "warning" | "success" })`
  - `Modal({ open, onClose, title, children })`, `Drawer({ open, onClose, title, children })`
  - `Pagination({ page, pageSize, total, onPageChange })`
  - `Tabs({ items: { id: string; label: string }[]; value: string; onChange })`
  - `EmptyState({ title, description, action? })`, `Spinner`, `ToastProvider` + `useToast()`

- [ ] **Step 1: Replace package.json for Next**

```json
{
  "name": "personal-agent-dashboard",
  "private": true,
  "version": "0.3.0",
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start --port 3000",
    "format": "prettier --write .",
    "format:check": "prettier --check ."
  },
  "dependencies": {
    "next": "^15.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.7.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "prettier": "^3.0.0"
  },
  "engines": { "node": ">=22.12.0" }
}
```

- [ ] **Step 2: Add `next.config.ts` with local API rewrite**

```ts
import type { NextConfig } from "next";

const backend = process.env.PERSONAL_AGENT_BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
```

- [ ] **Step 3: Add tokens + root layout**

Use CSS variables in `styles/tokens.css`:

```css
:root {
  --canvas: #f3f6f8;
  --surface: #ffffff;
  --ink: #14212b;
  --muted: #5b6b76;
  --accent: #0f6b6b;
  --accent-soft: #d7efef;
  --border: #d7e0e6;
  --danger: #b42318;
  --warning: #b54708;
  --radius: 12px;
  --font-display: var(--font-display);
  --font-ui: var(--font-ui);
}
```

Root `app/layout.tsx`: load one display font (e.g. `Newsreader` or `Fraunces`) and one UI sans (e.g. `Source Sans 3` or `IBM Plex Sans`) via `next/font/google`. Import `globals.css` that imports Tailwind + tokens. Soft canvas gradient background on `body`.

- [ ] **Step 4: Implement UI primitives**

Implement each file under `components/ui/` as small client/server-safe components. `Modal`, `Drawer`, `ToastProvider` are `"use client"`. Keep classNames token-based; no purple/glow.

- [ ] **Step 5: Smoke build**

Run from `frontend/`:

```bash
npm install
npm run build
```

Expected: Next build succeeds (placeholder `app/page.tsx` saying “AURA” is fine until Task 4).

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(frontend): scaffold Next.js App Router with design tokens and UI primitives"
```

---

### Task 2: API client, capabilities, auth session

**Files:**
- Create: `frontend/lib/api/types.ts`, `client.ts`, `auth.ts`, `status.ts`, `frontend/lib/capabilities.ts`, `frontend/lib/auth/session.ts`, `frontend/lib/pagination.ts`
- Create: `frontend/.env.local.example`

**Interfaces:**
- Produces:
  - `api<T>(path: string, options?: RequestInit): Promise<T>`
  - `getAuth(): Promise<AuthStatus>` where `AuthStatus = { authenticated: boolean; registered: boolean; user: { name: string; email: string } | null; email_required: boolean }`
  - `login(email: string | null, password: string): Promise<{ authenticated: true; user: User }>`
  - `register(name: string, email: string, password: string): Promise<{ registered: true }>`
  - `logout(): Promise<void>`
  - `getStatus(): Promise<StatusPayload>` (matches backend `/api/status` fields used by UI)
  - `capabilities` object: `{ chat: "api"; tasks: "api"; activity: "api"; telegram: "api"; google: "mock"; linkedin: "mock"; facebook: "mock" }`
  - `paginate<T>(items: T[], page: number, pageSize: number): { items: T[]; total: number; page: number; pageSize: number }`

- [ ] **Step 1: Write `lib/api/client.ts`**

```ts
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${API_BASE}/api${path}`;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    credentials: "include",
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    body: options.body === undefined ? undefined : (options.body as BodyInit),
  });
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    throw new ApiError("The backend returned an unreadable response.", response.status);
  }
  if (!response.ok) {
    const detail = (data as { detail?: string | { msg: string }[] })?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg).join(". ")
      : typeof detail === "string"
        ? detail
        : `Request failed (${response.status}).`;
    throw new ApiError(message, response.status);
  }
  return data as T;
}
```

Note: for POST bodies, callers pass `JSON.stringify(payload)` as `body`.

- [ ] **Step 2: Implement auth + status + capabilities + paginate helpers**

Wire `auth.ts` to `GET /auth`, `POST /login`, `POST /register`, `POST /logout`. Types match backend responses. `capabilities.ts` exports the locked flags. `pagination.ts` exports `paginate`.

- [ ] **Step 3: Manual sanity check**

With backend on `:8000` and `npm run dev`, from browser console or a temporary test page call `getAuth()` — expect JSON without CORS errors (rewrite proxies).

- [ ] **Step 4: Commit**

```bash
git add frontend/lib frontend/.env.local.example
git commit -m "feat(frontend): add typed API client, capabilities, and pagination helpers"
```

---

### Task 3: Auth pages (login + register)

**Files:**
- Create: `frontend/app/(auth)/layout.tsx`, `login/page.tsx`, `register/page.tsx`, `features/auth/login-form.tsx`, `register-form.tsx`, `use-auth.ts`
- Modify: middleware optional — prefer client gate in `(app)/layout` (Task 4) + redirect from auth pages when already authenticated

**Interfaces:**
- Consumes: `getAuth`, `login`, `register` from Task 2
- Produces: `useAuth()` → `{ status, loading, error, refresh, login, register, logout }`

- [ ] **Step 1: Build auth layout**

Centered brand-forward layout: AURA wordmark hero-level, soft canvas, single column form. No dashboard chrome.

- [ ] **Step 2: Login + register forms**

- Login: email (if `email_required`), password, submit → `login` → `router.replace("/")`
- Register: name, email, password → `register` → redirect to `/login` with success note
- Map `ApiError` 409 on register to “Registration is closed” + link to login
- Inline field errors; password visibility toggle

- [ ] **Step 3: Verify manually**

```bash
# terminal A
cd backend && personal-agent dashboard
# terminal B
cd frontend && npm run dev
```

Open `http://127.0.0.1:3000/login` — login with existing owner or register if none.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(auth\) frontend/features/auth
git commit -m "feat(frontend): add Next.js login and register against backend auth"
```

---

### Task 4: App shell (sidebar, header, notifications, profile)

**Files:**
- Create: `frontend/app/(app)/layout.tsx`, all of `components/shell/*`, `lib/mocks/notifications.ts`
- Modify: `app/page.tsx` → move Overview placeholder under `(app)/page.tsx`

**Interfaces:**
- Consumes: `useAuth`, `paginate`, mock notifications
- Produces: `DashboardLayout` wrapping children; nav items exactly: Overview `/`, Chat `/chat`, Tasks `/tasks`, Activity `/activity`, Connections `/connections`, Settings `/settings`
- NotificationsDrawer: paginated mock+approval counts; items link to `/tasks`, `/activity`, or `/connections/...`
- ProfileMenu: Account → `/settings?section=account`, Settings → `/settings`, Sign out → `logout()` → `/login`

- [ ] **Step 1: Auth gate layout**

`(app)/layout.tsx` is `"use client"` or uses a small `AuthGate` client component: while loading show Spinner; if not authenticated `redirect("/login")`; else render `DashboardLayout` with user.

- [ ] **Step 2: Sidebar + header**

Light professional shell: brand **AURA** prominent in sidebar; active route indicator with short motion; header title from pathname map; search input disabled/read-only placeholder “Search soon”; bell opens drawer; avatar opens profile menu.

- [ ] **Step 3: Notifications drawer**

Use `lib/mocks/notifications.ts` plus optional real approval count from `GET /api/approvals` when authenticated. Page size 10 via `paginate`. No separate notifications route.

- [ ] **Step 4: Verify shell**

Visit `/` after login — see sidebar + header; bell drawer opens/closes; sign out works.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/\(app\) frontend/components/shell frontend/lib/mocks/notifications.ts
git commit -m "feat(frontend): add authenticated dashboard shell with notifications and profile menu"
```

---

### Task 5: Overview (summary only)

**Files:**
- Create: `features/overview/overview-page.tsx`, `summary-stats.tsx`, `health-strip.tsx`
- Modify: `app/(app)/page.tsx` to render `OverviewPage`

**Interfaces:**
- Consumes: `getStatus`, `api` for tasks/approvals counts, capabilities
- Produces: Overview with greeting, ≤4 stat tiles (counts only), Ask agent CTA → `/chat`, health strip linking to connection details — **no** embedded chat/task tables

- [ ] **Step 1: Implement summary widgets**

Stat tiles: open tasks (API), pending approvals (API), Telegram configured/managed (status API), Google/Social as Preview. Health strip: one row of channel chips linking out.

- [ ] **Step 2: Verify**

Overview shows counts without listing full tasks; each CTA navigates to the owning page.

- [ ] **Step 3: Commit**

```bash
git add frontend/features/overview frontend/app/\(app\)/page.tsx
git commit -m "feat(frontend): add Overview summary page without duplicated feature boards"
```

---

### Task 6: Chat, Tasks, Activity

**Files:**
- Create: `lib/api/chat.ts`, `tasks.ts`, `activity.ts`
- Create: all files under `features/chat`, `features/tasks`, `features/activity`
- Create: `app/(app)/chat/page.tsx`, `tasks/page.tsx`, `activity/page.tsx`

**Interfaces:**
- `sendChat({ message, sessionId? })` → `POST /chat` or stream via `POST /chat/stream` (NDJSON lines: `delta` | `done` | `error`)
- `listTasks()`, `createTask()`, `patchTask(id, body)`
- `listApprovals()`, `decideApproval(id, decision: "approve" | "reject")`
- `listActivity()` → `GET /activity`
- Tasks page: `pageSize = 10`, `TaskApproveModal` for pending approvals
- Activity page: `pageSize = 15`, `ActivityDetailDrawer` for row detail

- [ ] **Step 1: API modules**

Port request shapes from existing Vite hooks; keep TypeScript types explicit in `lib/api/types.ts`.

- [ ] **Step 2: Chat page**

Single conversation column: message list + composer. Loading/empty/error states via shared UI. No tasks sidebar on this page.

- [ ] **Step 3: Tasks page**

Paginated tasks; separate “Approvals” section or filter tab **on the same page** (still one job: task governance). Approve/reject opens Modal — not a new route.

- [ ] **Step 4: Activity page**

Paginated timeline; click → Drawer with payload detail. Deep-link from notifications uses `?id=` optional highlight.

- [ ] **Step 5: Verify each route one job**

Confirm Overview does not embed these UIs; each page works independently with backend running.

- [ ] **Step 6: Commit**

```bash
git add frontend/features/chat frontend/features/tasks frontend/features/activity frontend/lib/api frontend/app/\(app\)/chat frontend/app/\(app\)/tasks frontend/app/\(app\)/activity
git commit -m "feat(frontend): add Chat, Tasks, and Activity pages with pagination and modals"
```

---

### Task 7: Connections (Telegram API + Google/Social mocks)

**Files:**
- Create: `lib/api/telegram.ts`, `lib/mocks/google.ts`, `lib/mocks/social.ts`
- Create: `features/connections/**`
- Create: connection routes under `app/(app)/connections/**`

**Interfaces:**
- Telegram API: `verifyTelegram()`, `startTelegram()`, `stopTelegram()`, `telegramActivity()`, plus status from `getStatus().telegram`
- Google mock: `{ gmail: Message[]; calendar: Event[]; drive: File[] }` with `paginate`
- Social mock: `{ connected: boolean; displayName: string; drafts: Draft[] }`
- `DraftPreviewModal` on LinkedIn/Facebook pages only
- `ChannelGrid` on `/connections` only — cards link to detail routes

- [ ] **Step 1: Connections directory**

Grid of Telegram / Google / LinkedIn / Facebook. Telegram shows real configured/managed; others show Preview badge.

- [ ] **Step 2: Telegram detail**

One page: identity verify, start/stop, status, recent activity list (paginated). No Google UI here.

- [ ] **Step 3: Google detail**

Subnav Tabs: Gmail | Calendar | Drive — one active list, paginated mock rows. Banner: Integration pending.

- [ ] **Step 4: LinkedIn + Facebook**

Connection summary + draft list; “Preview draft” opens `DraftPreviewModal`. No publishing calls.

- [ ] **Step 5: Verify no duplicates**

No top-level `/telegram` route; Content Studio only as modal on social pages.

- [ ] **Step 6: Commit**

```bash
git add frontend/features/connections frontend/lib/api/telegram.ts frontend/lib/mocks frontend/app/\(app\)/connections
git commit -m "feat(frontend): add Connections directory with Telegram API and Google/social mocks"
```

---

### Task 8: Settings + polish + local docs

**Files:**
- Create: `features/settings/**`, `app/(app)/settings/page.tsx`
- Modify: `frontend/README.md` only (local Next.js run instructions)
- Do **not** modify `docs/deploy.md`, CI, or `vercel.json`

**Interfaces:**
- Settings sections via `?section=account|appearance|runtime|permissions` + `SettingsSubnav`
- Account reads `user` from auth; Appearance documents tokens (no persistence required); Runtime shows `getStatus()` fields; Permissions is static honest copy

- [ ] **Step 1: Settings page with subnav sections**

One settings route; section switch does not duplicate Profile elsewhere.

- [ ] **Step 2: Motion polish**

Add CSS transitions: sidebar active indicator, drawer slide, subtle page fade on main content. Keep to 2–3 motions.

- [ ] **Step 3: Update `frontend/README.md`**

Document: Node 22+, `npm install`, `npm run dev` on `:3000`, backend on `:8000`, `PERSONAL_AGENT_BACKEND_URL`, auth flow, capability flags. State clearly that production Vercel/CI cutover is not included.

- [ ] **Step 4: Final local verification checklist**

- `/login`, `/register`
- Shell: nav, bell, profile, sign out
- Overview summaries only
- Chat / Tasks (modal) / Activity (drawer) against backend
- Connections + Telegram + Google/Social mocks
- Settings sections
- `npm run build` succeeds
- Confirm git diff does **not** include `.github/`, `vercel.json`, `render.yaml`

- [ ] **Step 5: Commit**

```bash
git add frontend/features/settings frontend/app/\(app\)/settings frontend/README.md
git commit -m "feat(frontend): add Settings sections and local Next.js run docs"
```

---

## Spec coverage check

| Spec requirement | Task |
| --- | --- |
| Replace frontend with Next.js App Router | 1 |
| No CI/Vercel/env edits | Global + Task 8 |
| Real auth API | 2–3 |
| Shell: sidebar, header, notifications, profile | 4 |
| Hybrid nav + one job per page | 4–7 |
| Overview summary only | 5 |
| Chat/Tasks/Activity + pagination/modals | 6 |
| Connections Telegram API + Google/social mocks | 7 |
| Draft preview modal on social only | 7 |
| Settings single route + subnav | 8 |
| Light professional visual system | 1, 4, 8 |
| Maintainable feature modules | File structure + all tasks |

## Placeholder / consistency review

- API path helpers consistently use `api("/auth")` style paths without duplicating `/api` prefix beyond `apiUrl`.
- Capability flags named `telegram|google|linkedin|facebook|chat|tasks|activity`.
- Approvals live on Tasks via modal only.
- Notifications are drawer-only.
