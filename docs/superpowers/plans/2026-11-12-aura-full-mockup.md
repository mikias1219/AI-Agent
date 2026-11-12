# AURA Full Mockup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the full mockup (`AURA — Today v2 and Chat v2 mockups.html`) on one branch with backend contracts so every screen shows real or honestly unavailable data.

**Architecture:** Single branch `feature/aura-full-mockup`. Tokens and shell first; then Today BFF and agent control; then Chat cards; then Goals/Plans/Suggestions/Routines; then Calendar/Mail/Settings polish. Application layer owns aggregates (`TodayService`); tools still go through `ToolRegistry`; UI cards only from `result_type`.

**Tech Stack:** FastAPI + SQLAlchemy/Alembic (SQLite+Postgres), Next.js App Router, Playwright, pytest, FakeProvider offline tests.

**Spec:** `docs/superpowers/specs/2026-11-12-aura-full-mockup-design.md`

## Global Constraints

- No mock calendar/email/task facts; say `not_connected` / unavailable when sources fail
- Every tool call through `ToolRegistry.execute`; hard ceilings always need approval
- Chat cards from `result_type` only (never keyword match on tool names)
- Proactive output respects quiet hours and daily cap; Pause stops routines/background runs
- Tests offline: FakeProvider, temp DB, mocked HTTP; Alembic migrations SQLite+Postgres
- One big-bang merge at the end; atomic conventional commits per task
- Work from repo root `/home/mikias/Desktop/AI Agent` on branch `feature/aura-full-mockup`

---

## File map (create / modify)

| Area | Paths |
| --- | --- |
| Tokens / atoms | `frontend/styles/tokens.css`, `frontend/components/ui/*`, `frontend/app/layout.tsx` |
| Shell | `frontend/components/shell/nav.ts`, `app-sidebar.tsx`, `app-header.tsx`, `dashboard-layout.tsx`, `quick-ask-drawer.tsx` (new) |
| Today | `frontend/features/today/today-page.tsx`, `backend/.../services/today_service.py` (new), `app.py` `GET /api/today` |
| Chat | `frontend/features/chat/*`, `chat-cards-logic.ts` |
| Goals/Plans | `backend/.../domain/goals.py` (new), stores, `GET/POST /api/goals`, `/api/plans` |
| Suggestions/Inbox | `backend/.../domain/suggestions.py` (new), `GET /api/inbox`, `GET /api/suggestions` |
| Agent control | `backend/.../services/agent_control_service.py` (new), `GET/PATCH /api/agent/control` |
| Calendar/Mail FE | `frontend/app/(app)/calendar`, `mail` |
| Routines | rename automations UI + API alias `/api/routines` |
| Docs | ADRs `0016+`, README/feature-status, this plan’s commits |

---

### Task 0: Branch + design tokens + shared atoms

**Files:**
- Create: `frontend/components/ui/status-chip.tsx`, `frontend/components/ui/compact-row.tsx`
- Modify: `frontend/styles/tokens.css`, `frontend/app/layout.tsx`, `frontend/app/globals.css`
- Test: `frontend/components/ui/status-chip.test.ts` (optional vitest) or visual smoke via existing component tests

**Interfaces:**
- Produces: CSS vars `--accent:#0F766E`, `--warning:#B45309`, `--danger:#B42318`, `--canvas:#F7F8FA`, `--ink:#0F1720`, `--muted:#52606D`, `--border:#E4E7EB`, `--accent-soft:#E6F4F2`, `--success:#15803D`
- Produces: `StatusChip({ tone: "warning"|"success"|"accent"|"danger"|"neutral", children })`, `CompactRow({ title, meta, chip, onClick })`

- [ ] **Step 1: Create branch from main**

```bash
cd "/home/mikias/Desktop/AI Agent"
git checkout main && git pull
git checkout -b feature/aura-full-mockup
```

- [ ] **Step 2: Update tokens to mockup palette**

Replace light theme values in `frontend/styles/tokens.css` with the hex table above (keep existing var names used across the app).

- [ ] **Step 3: Add StatusChip + CompactRow**

Implement presentational components using `var(--*)` only; no hardcoded hex in JSX.

- [ ] **Step 4: Fonts**

Point UI sans at Inter (or `next/font/google` Inter) in `app/layout.tsx`; remove Newsreader from shell if it conflicts with mockup.

- [ ] **Step 5: Commit**

```bash
git add frontend/styles/tokens.css frontend/components/ui frontend/app/layout.tsx frontend/app/globals.css
git commit -m "feat(ui): mockup design tokens and shared atoms"
```

---

### Task 1: Shell — grouped nav, header chrome, remove bell drawer

**Files:**
- Modify: `frontend/components/shell/nav.ts`, `app-sidebar.tsx`, `app-header.tsx`, `dashboard-layout.tsx`
- Create: `frontend/components/shell/quick-ask-drawer.tsx`, `frontend/components/shell/autonomy-chip.tsx`
- Delete usage: `frontend/components/shell/notifications-drawer.tsx` from layout (file may remain unused until deleted)
- Create routes stubs if missing: `frontend/app/(app)/goals/page.tsx`, `calendar/page.tsx`, `mail/page.tsx`, `routines/page.tsx` (redirect from automations)
- Test: `frontend/e2e/smoke.spec.ts` — extend nav checks

**Interfaces:**
- Consumes: existing `getStatus()`, later `GET /api/agent/control` (Task 2 may stub FE with local defaults until API lands)
- Produces: `NAV_GROUPS` structure; `QuickAskDrawer` opens chat run with `origin: "quick_ask"`

- [ ] **Step 1: Rewrite `nav.ts` groups**

```ts
export const NAV_GROUPS = [
  { id: "primary", items: [
    { href: "/", label: "Today" },
    { href: "/chat", label: "Chat" },
    { href: "/inbox", label: "Inbox", badgeKey: "needsYou" },
  ]},
  { id: "my-work", label: "My work", items: [
    { href: "/tasks", label: "Tasks" },
    { href: "/goals", label: "Goals" },
    { href: "/calendar", label: "Calendar" },
    { href: "/mail", label: "Mail" },
  ]},
  { id: "aura", label: "AURA", items: [
    { href: "/memory", label: "Memory" },
    { href: "/routines", label: "Routines" },
    { href: "/activity", label: "Activity" },
  ]},
  { id: "footer", items: [
    { href: "/connections", label: "Connections" },
    { href: "/settings", label: "Settings" },
    { href: "/help", label: "Help" },
  ]},
] as const;
```

- [ ] **Step 2: Sidebar renders groups + Inbox badge from needs-you count**

- [ ] **Step 3: Header — quick-ask, AutonomyChip, Pause, Listening; remove bell**

Quick-ask focuses input or opens drawer on Cmd/Ctrl+K. Pause calls control API when available; until Task 2, disable with tooltip “Coming with agent control”.

- [ ] **Step 4: `QuickAskDrawer` — side drawer that starts `POST /api/runs` and streams events**

Reuse chat run helpers from `lib/api/runs.ts`.

- [ ] **Step 5: Redirect `/automations` → `/routines`; stub Goals/Calendar/Mail pages with loading/empty**

- [ ] **Step 6: Playwright nav smoke at 1280 and 360**

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(shell): grouped nav, quick-ask drawer, autonomy chrome"
```

---

### Task 2: Backend — agent control + today aggregate + agenda + active run

**Files:**
- Create: `backend/src/personal_agent/application/services/agent_control_service.py`
- Create: `backend/src/personal_agent/application/services/today_service.py`
- Create: `backend/migrations/versions/20261112_07_agent_control.py` (or next free revision after `20261112_06`)
- Modify: `backend/src/personal_agent/presentation/web/app.py` — routes
- Modify: `backend/src/personal_agent/app/container.py` — wire services
- Modify: `backend/src/personal_agent/application/tools/registry.py` — respect `paused` + ceilings hook
- Test: `backend/tests/unit/test_agent_control.py`, `backend/tests/unit/test_today_service.py`

**Interfaces:**
- Produces:

```python
@dataclass
class AgentControlState:
    autonomy_preset: str  # ask_first | balanced | proactive
    paused: bool
    budgets: dict[str, int]  # commits_used, commits_cap, proactive_used, proactive_cap, ...

class AgentControlService:
    def get(self, owner_id: str) -> AgentControlState: ...
    def patch(self, owner_id: str, *, autonomy_preset: str | None = None, paused: bool | None = None) -> AgentControlState: ...

class TodayService:
    def build(self, owner_id: str) -> dict[str, Any]: ...
```

- Routes: `GET/PATCH /api/agent/control`, `GET /api/today`, `GET /api/calendar/agenda?limit=3`, `GET /api/runs/active`

- [ ] **Step 1: Failing tests for control pause and today payload keys**

```python
def test_pause_blocks_registry_execute(session_factory):
    # set paused True; execute read tool → PermissionDeniedError or explicit paused error
    ...

def test_today_build_has_required_keys(session_factory):
    payload = today_service.build("dashboard")
    assert set(payload) >= {
        "greeting", "needs_you", "now_next", "plan", "goals",
        "since_last_looked", "onboarding", "connections", "briefing",
    }
```

- [ ] **Step 2: Migration — columns or `agent_state` JSON on profile**

Prefer `owner_profiles.agent_control_json` Text blob for SQLite/Postgres simplicity unless a dedicated table is clearer.

- [ ] **Step 3: Implement `AgentControlService` + registry gate when `paused`**

- [ ] **Step 4: Implement `TodayService.build` composing briefing document, approvals (≤3), agenda, active run, tasks today, connection warnings**

Goals/suggestions arrays empty `[]` until later tasks.

- [ ] **Step 5: Agenda helper — owner timezone day window via Google client or empty + `connected: false`**

- [ ] **Step 6: `GET /api/runs/active` — latest run with status running or awaiting_approval for owner**

- [ ] **Step 7: Wire container + routes; run pytest**

```bash
cd backend && .venv/bin/python -m pytest tests/unit/test_agent_control.py tests/unit/test_today_service.py -q
```

- [ ] **Step 8: Commit**

```bash
git commit -m "feat(api): agent control, today aggregate, agenda, active run"
```

---

### Task 3: Today v2 UI

**Files:**
- Modify: `frontend/features/today/today-page.tsx`, `frontend/lib/api/today.ts` (new)
- Modify: `frontend/lib/api/automations.ts` only if still used for fallback
- Test: Playwright today section visibility; unit not required if e2e covers

**Interfaces:**
- Consumes: `GET /api/today`, `POST /api/runs/{id}/cancel` for Stop

- [ ] **Step 1: `lib/api/today.ts` typed client for TodayPayload**

- [ ] **Step 2: Rebuild Today layout per mockup sections; render `briefing.sections`; Needs you ≤3; Now/next + Stop; plan tasks; omit empty sections without CTA**

- [ ] **Step 3: Remove permanent fake agenda empty; use `connections` / agenda `connected` for Connect Google**

- [ ] **Step 4: Skeletons per section while loading**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(today): Today v2 from /api/today"
```

---

### Task 4: Chat v2 — thread list + action cards

**Files:**
- Modify: `frontend/features/chat/chat-page.tsx`, `message-list.tsx`, `chat-cards-logic.ts`, `chat-cards.tsx`, `run-trail.ts`
- Modify: backend tools `result_type` for any missing kinds used in UI
- Test: `frontend/features/chat/chat-cards.test.ts`

**Interfaces:**
- Extends `ChatCard` kinds with actions callbacks optional: `onApprovePlan`, etc.
- Plan approve may call future `/api/plans/{id}/approve` (stub button disabled until Task 5) or approval APIs

- [ ] **Step 1: Chat list aside from `GET /api/conversations`**

- [ ] **Step 2: Expand `cardsFromSteps` + `ChatCards` UI for plan/approval/receipt/draft/calendar/task with primary buttons**

Unknown `result_type` → generic receipt.

- [ ] **Step 3: Wire approval buttons to existing approval APIs; plan buttons no-op or disabled until Task 5**

- [ ] **Step 4: Unit test card kinds; commit**

```bash
git commit -m "feat(chat): Chat v2 thread list and typed action cards"
```

---

### Task 5: Goals + Plans backend and UI

**Files:**
- Create: `backend/src/personal_agent/domain/goals.py`, persistence models/migration, `goal_service.py`, `plan_service.py`
- Create: `frontend/features/goals/goals-page.tsx`, `frontend/lib/api/goals.ts`
- Modify: `app.py` routes `/api/goals`, `/api/plans`
- Register tools: `goal_create`, `plan_propose` with `result_type` `plan` / task links
- Test: `backend/tests/unit/test_goals_plans.py`, eval scenario JSON

**Interfaces:**

```python
@dataclass
class Goal:
    id: str
    owner_user_id: str
    title: str
    success_criteria: list[str]
    progress: float
    status: str  # active | paused | done
    next_step: str

@dataclass
class PlanStep:
    id: str
    title: str
    tool_name: str | None
    access_kind: str
    status: str  # planned | running | needs_ok | done | failed
    depends_on: list[str]

@dataclass
class Plan:
    id: str
    goal_id: str | None
    owner_user_id: str
    steps: list[PlanStep]
    status: str
```

- [ ] **Step 1: Failing unit tests for create goal + approve plan authorizes prepare only**

- [ ] **Step 2: Migration + stores + services**

- [ ] **Step 3: HTTP API + tools + eval scenario**

- [ ] **Step 4: Goals page UI (list + detail drawer with plan steps)**

- [ ] **Step 5: Enable Chat plan card Approve → `POST /api/plans/{id}/approve`**

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(goals): goals, plans, and plan card approve"
```

---

### Task 6: Suggestions + unified Inbox

**Files:**
- Create: suggestion domain/store/service + migration
- Modify: `app.py` — `GET /api/suggestions`, `POST /api/suggestions/{id}/accept|dismiss`, `GET /api/inbox`
- Modify: `frontend/features/inbox/inbox-page.tsx`, `TodayService` needs_you merge
- Test: `backend/tests/unit/test_suggestions_inbox.py`

**Interfaces:**

```python
@dataclass
class Suggestion:
    id: str
    owner_user_id: str
    kind: str
    title: str
    reason: str
    source: str  # required citation
    status: str  # new | accepted | dismissed | expired
    proposed_action: dict[str, Any]
    expires_at: datetime | None
```

`GET /api/inbox?tab=open|done` → `{ items: [...], counts: { open: n } }` ordered by urgency.

- [ ] **Step 1–5: TDD service → API → Inbox UI (Needs you | Done) → wire Today needs_you → commit**

```bash
git commit -m "feat(inbox): suggestions and unified urgency inbox"
```

---

### Task 7: Calendar + Mail screens

**Files:**
- Create: `frontend/app/(app)/calendar/page.tsx`, `features/calendar/calendar-page.tsx`
- Create: `frontend/app/(app)/mail/page.tsx`, `features/mail/mail-page.tsx`
- Reuse: `GET /api/google/calendar`, gmail list/search/read, status
- Optional: `GET /api/calendar/agenda` for Today already done
- Test: Playwright disconnected shows Connect; connected lists items with mocked API in e2e if available

- [ ] **Step 1: Calendar week UI; proposals as dashed events when suggestion/plan provides them**

- [ ] **Step 2: Mail 3-pane; flag external/untrusted content; draft actions via existing approve flow**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(google-ui): calendar and mail screens"
```

---

### Task 8: Routines surface + quiet hours / cap enforcement

**Files:**
- Rename FE automations → routines; API alias `GET/PATCH /api/routines`
- Extend automation/routine model with quiet_hours + daily_cap fields (migration)
- Enforce in scheduler / proactive send path via `AgentControlService` budgets
- Test: unit quiet hours blocks send; cap increments

- [ ] **Steps: migration → enforcement tests → Routines page templates/Run now → commit**

```bash
git commit -m "feat(routines): routines UI and proactive quiet hours/cap"
```

---

### Task 9: Settings Permissions + first-run autonomy

**Files:**
- Modify: `frontend/features/settings/*`, onboarding wizard
- Wire AutonomyChip + Pause to live `/api/agent/control`
- Test: e2e pause then ensure routine tick does not telegram (unit-level sufficient)

- [ ] **Commit:** `feat(settings): permissions presets, budgets, autonomy onboarding`

---

### Task 10: Memory tabs, Activity human-first, Connections, Help

**Files:**
- Memory page tabs (facts / people / playbooks stub)
- Activity list: summary line first; ids in drawer only
- Connections: broken-only warnings pattern shared with Today
- Help: How AURA works matching mockup loop
- Commit: `feat(ux): memory tabs, activity clarity, help loop`

---

### Task 11: Docs, evals, CI green, merge prep

**Files:**
- ADRs `docs/adr/0016-today-aggregate.md`, `0017-agent-control.md`, `0018-goals-plans.md`, `0019-suggestions-inbox.md`
- Update `docs/superpowers/specs/2026-11-12-aura-full-mockup-design.md` status → Implemented when done
- README / feature-status / capabilities
- Full `pytest`, frontend `tsc`/`vitest`, e2e smoke
- Commit: `docs: ADRs and status for full mockup`
- Do **not** merge/push to `main` until user requests

---

## Spec coverage checklist

| Spec section | Task |
| --- | --- |
| §3 commit order | Tasks 0–11 |
| §4 tokens/atoms | Task 0 |
| §5 shell | Task 1 |
| §6 Today + `/api/today` | Tasks 2–3 |
| §7 Chat v2 | Task 4 (+5 for plan approve) |
| §8 other screens | Tasks 5–10 |
| §9 domain additions | Tasks 2, 5, 6, 8, 9 |
| §10 truth/safety | Global + Tasks 2, 8, 9 |
| §11 testing | Per-task + Task 11 |
| §12 docs | Task 11 |

## Placeholder scan

No TBD/TODO steps; later tasks may leave plan-approve disabled until Task 5 (explicit).

---

**Plan complete and saved to `docs/superpowers/plans/2026-11-12-aura-full-mockup.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
