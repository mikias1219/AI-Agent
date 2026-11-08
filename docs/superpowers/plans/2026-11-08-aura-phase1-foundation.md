# AURA Phase 1 Product Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the existing React dashboard into an AURA product shell with dark-navy design, grouped module navigation, Overview from real APIs only, and honest unavailable states—without backend or stack migration changes.

**Architecture:** Keep hash routing, JSX, and `useWorkspaceData` polling. Expand `navigation.js` into grouped IA. Add shared `EmptyState` / `ModulePlaceholder` / `StatusPill`. Restyle shell + pages via CSS tokens. Placeholder routes for unbuilt modules. Telegram remains top-level.

**Tech Stack:** React 19, Vite 6, Tailwind CSS 4, Lucide, existing FastAPI cookie APIs, Playwright e2e.

## Global Constraints

- Approach A only: no TypeScript, React Router, TanStack Query, shadcn, RHF, or Zod.
- No new backend endpoints.
- No fake charts, fake worker online state, or hardcoded activity counts.
- Worker status must show **Not connected yet**.
- Telegram stays a top-level nav item; Inbox placeholder links to it.
- Approvals stay on Tasks & Goals.
- Branding: **AURA**; Inter font; dark navy + subtle violet/blue accents.
- Preserve chat, tasks, Telegram, auth, activity behavior.

## File map

| File | Responsibility |
| --- | --- |
| `frontend/index.html` | Inter, theme-color, AURA title |
| `frontend/src/shared/styles/globals.css` | Dark tokens + component utilities |
| `frontend/src/shared/components/ui/Brand.jsx` | AURA mark |
| `frontend/src/shared/components/ui/Avatar.jsx` | Dark-theme avatar |
| `frontend/src/shared/components/ui/PageHeading.jsx` | Dark text colors |
| `frontend/src/shared/components/ui/EmptyState.jsx` | Shared empty copy |
| `frontend/src/shared/components/ui/ModulePlaceholder.jsx` | Later-phase module page |
| `frontend/src/shared/components/ui/StatusPill.jsx` | Status chip |
| `frontend/src/app/routing/navigation.js` | Grouped routes + labels |
| `frontend/src/app/layouts/DashboardLayout.jsx` | Sidebar sections + status strip |
| `frontend/src/app/App.jsx` | Route wiring + document title |
| `frontend/src/features/home/pages/HomePage.jsx` | Overview from real data |
| `frontend/src/features/*/pages/*Placeholder*.jsx` | Module placeholders |
| Existing feature pages | Restyle classes only |
| `frontend/tests/e2e/workspace.spec.js` | Updated labels |
| `docs/architecture.md` | Brief AURA shell note |

---

### Task 1: Design tokens, Inter, Brand, shared primitives

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/shared/styles/globals.css`
- Modify: `frontend/src/shared/components/ui/Brand.jsx`
- Modify: `frontend/src/shared/components/ui/Avatar.jsx`
- Modify: `frontend/src/shared/components/ui/PageHeading.jsx`
- Create: `frontend/src/shared/components/ui/EmptyState.jsx`
- Create: `frontend/src/shared/components/ui/ModulePlaceholder.jsx`
- Create: `frontend/src/shared/components/ui/StatusPill.jsx`

**Interfaces:**
- Produces: `EmptyState({ title, children })`, `ModulePlaceholder({ title, description, action })`, `StatusPill({ label, tone })` where `tone` is `'neutral' | 'accent' | 'warning' | 'danger' | 'success'`
- Brand renders text **AURA**

- [ ] **Step 1: Update `index.html`**

Load Inter from fonts.googleapis.com, set `theme-color` to `#0B1220`, title to `AURA · Personal AI Operating System`.

- [ ] **Step 2: Replace theme tokens in `globals.css`**

Dark navy foundation; accent violet/blue; restyle `.card`, `.primary`, `.secondary`, `.field`, `.label`, `.eyebrow` for dark surfaces.

- [ ] **Step 3: Update Brand / Avatar / PageHeading; add EmptyState, ModulePlaceholder, StatusPill**

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/src/shared/
git commit -m "feat(ui): add AURA dark design tokens and shared primitives"
```

---

### Task 2: Navigation IA and DashboardLayout

**Files:**
- Modify: `frontend/src/app/routing/navigation.js`
- Modify: `frontend/src/app/layouts/DashboardLayout.jsx`

**Interfaces:**
- Produces: `navSections` array of `{ id, label, items: [[routeId, label, Icon], ...] }`; `validRoutes` includes all route ids + auth routes; keep exporting helpers App needs (`authRoutes`, `validRoutes`, flat lookup for titles).

- [ ] **Step 1: Rewrite `navigation.js` with grouped sections**

Routes: today, agent, telegram, inbox, tasks, calendar, growth, automation, memory, knowledge, connections, activity, settings. Include `studio` in `validRoutes` mapping to automation for legacy hashes.

- [ ] **Step 2: Restyle `DashboardLayout`**

Grouped nav labels; sidebar footer status strip (provider, model, Worker: Not connected yet, Telegram from `status.telegram`); dark surfaces; keep Open menu / Log out / approval badge on Tasks.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/routing/navigation.js frontend/src/app/layouts/DashboardLayout.jsx
git commit -m "feat(ui): add AURA sidebar navigation and system status strip"
```

---

### Task 3: Overview, placeholders, restyle existing pages

**Files:**
- Modify: `frontend/src/features/home/pages/HomePage.jsx`
- Modify: auth, chat, telegram, tasks, connections, activity pages (className/visual only)
- Create placeholders under:
  - `frontend/src/features/inbox/pages/InboxPage.jsx`
  - `frontend/src/features/calendar/pages/CalendarPage.jsx`
  - `frontend/src/features/memory/pages/MemoryPage.jsx`
  - `frontend/src/features/knowledge/pages/KnowledgePage.jsx`
  - `frontend/src/features/growth/pages/GrowthPage.jsx`
  - `frontend/src/features/automation/pages/AutomationPage.jsx`
  - `frontend/src/features/settings/pages/SettingsPage.jsx`
- Modify or retire nav usage of `ContentStudioPage` (redirect/reuse Automation placeholder)

**Interfaces:**
- `HomePage` props unchanged plus use `approvals` and `activity` if passed from App (extend props as needed).
- `SettingsPage({ user })` shows name/email; worker controls unavailable.
- `InboxPage({ go })` includes button to `go('telegram')`.

- [ ] **Step 1: Rebuild Overview (`HomePage`) with real-data sections and unavailable blocks**

- [ ] **Step 2: Add placeholder pages via `ModulePlaceholder`**

- [ ] **Step 3: Restyle existing interactive pages for dark theme without behavior changes**

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/
git commit -m "feat(ui): rebuild Overview and add AURA module placeholders"
```

---

### Task 4: Wire App.jsx and document titles

**Files:**
- Modify: `frontend/src/app/App.jsx`

- [ ] **Step 1: Import new pages; render by route id; map `studio` → Automation**

- [ ] **Step 2: Pass `approvals` and `activity` into Overview; title suffix `· AURA`**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/App.jsx
git commit -m "feat(ui): wire AURA module routes in App shell"
```

---

### Task 5: Docs + Playwright + verify

**Files:**
- Modify: `docs/architecture.md`
- Modify: `frontend/tests/e2e/workspace.spec.js`

- [ ] **Step 1: Update e2e selectors**

- Nav: `Tasks & Goals` instead of `Tasks & approvals` if label changed.
- Keep Telegram top-level button name `Telegram`.
- Update Overview heading assertions to match new copy while preserving register → chat → tasks → telegram flow.
- Auth headings may change with restyle—update expectations to match final copy.

- [ ] **Step 2: Note in `docs/architecture.md` that UI is AURA shell; worker not connected yet**

- [ ] **Step 3: Run verification**

```bash
npm --prefix frontend run build
npm --prefix frontend run format:check
npm --prefix frontend run test:e2e
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture.md frontend/tests/e2e/workspace.spec.js
git commit -m "test: align Playwright and docs with AURA Phase 1 shell"
```

---

## Spec coverage checklist

| Spec requirement | Task |
| --- | --- |
| Dark navy + Inter + AURA brand | 1 |
| Grouped sidebar IA | 2 |
| Telegram top-level | 2 |
| Worker Not connected yet | 2 |
| Overview real data / unavailable | 3 |
| Placeholders | 3 |
| Settings profile + unavailable worker | 3 |
| Wire routes | 4 |
| e2e + architecture note | 5 |
| No backend / no stack migration | Global |
