# AURA full mockup redesign (Today v2, Chat v2, shell, and supporting screens)

**Date:** 2026-11-12  
**Status:** Implemented on `feature/aura-full-mockup` (Approach A Tasks 0–11)  
**Source mockup:** `AURA — Today v2 and Chat v2 mockups.html` (22 frames)  
**Proposal:** `docs/AURA_PROPOSAL.md` Parts 4, 6–8 (UIX, UXC, V1–V3, A1–A5, A4)  
**Prerequisites:** Phase 4 repairs R1–R4 on `main`  
**Delivery:** Approach A — single branch `feature/aura-full-mockup`, dependency-ordered commits, one merge/PR at the end (big-bang ship)

---

## 1. Goal

Bring the product UI to parity with the full mockup board and align the backend so every visible surface reads real data or an honest unavailable state. No fake calendar, email, or task facts. Chat cards continue to render from `result_type` (R4).

## 2. Non-goals (unless explicitly pulled in later)

- Pixel-perfect Telegram mobile chrome as a product screen (document in Help; keep existing channel behavior).
- Optional A7 capture / A8 roles (proposal optional).
- Live usability test (§46) before merge — run after the branch ships; record ADR then.
- Mid-branch production deploys (big-bang; deploy when merging to `main`).

## 3. Branch and commit order

Branch: `feature/aura-full-mockup`.

Implement in this order (each is one or more conventional commits):

| Step | Focus | Exit check |
| --- | --- | --- |
| 0 | Design tokens + shared atoms (chips, rows, drawer, buttons) from Components frame | Story/unit smoke; no screen rewrite yet |
| 1 | Shell: grouped nav, header (quick-ask → side-drawer chat, autonomy chip, Pause, Listening), rename Automations→Routines, remove bell drawer | Playwright nav 360/768/1280 |
| 2 | Backend contracts: `/api/today`, agenda, active run, inbox aggregate, agent control stub | API tests offline |
| 3 | Today v2 UI on `/api/today` | No permanent fake agenda; sections from real/unavailable |
| 4 | Chat v2: thread list + richer cards (plan/approval/receipt/…) | Cards from `result_type` only |
| 5 | Goals + Plans entities + UI | CRUD + plan card actions |
| 6 | Suggestions + unified Inbox | Needs-you + Done tab |
| 7 | Calendar + Mail screens (Google-backed) | Connect CTA when disconnected |
| 8 | Routines engine surface + quiet hours/cap on control plane | Routines page + enforcement hooks |
| 9 | Settings Permissions + first-run autonomy step | Presets + pause + budgets visible |
| 10 | Memory tabs (facts/people/playbooks as far as MEM allows), Activity human-first, Connections polish, Help | Loading/empty/error everywhere |
| 11 | Evals/scenarios for new tools; ADRs; README/feature status | CI green on the branch |

## 4. Visual system (mockup Components)

Map mockup palette into `frontend/styles/tokens.css` (and dark later if needed):

| Token | Hex (light) | Role |
| --- | --- | --- |
| `--canvas` / bg | `#F7F8FA` | Page |
| `--surface` | `#FFFFFF` | Cards, nav |
| `--ink` | `#0F1720` | Primary text |
| `--muted` | `#52606D` | Secondary |
| `--border` | `#E4E7EB` | Rules |
| `--accent` | `#0F766E` | Primary actions, active nav |
| `--accent-soft` | `#E6F4F2` | Soft selection |
| `--success` | `#15803D` | Listening / Done |
| `--warning` | `#B45309` | Needs you |
| `--danger` | `#B42318` | Failed / overdue |

**Typography:** Prefer Inter (or closest licensed stack already in repo) for UI; keep one display face only if it does not fight the mockup. Type scale: display ~30, title 18, body 14, small 13, caption 12.

**Shared components:** status chip (`.t` variants), compact row, full drawer, segmented control, toggle, progress, autonomy chip, Pause button, Listening pill, approval/plan/receipt cards.

## 5. Navigation and shell (V1 / UXC-01, 03, 05)

### Nav groups

- **Primary:** Today, Chat, Inbox (badge = needs-you count only)
- **My work:** Tasks, Goals, Calendar, Mail
- **AURA:** Memory, Routines, Activity
- **Footer:** Connections, Settings, Help

Rename route label Automations → Routines (`/routines` preferred; redirect `/automations`).

### Header (every app screen)

- Quick-ask field (Cmd/Ctrl+K) opens **side-drawer chat** (reuses `POST /api/runs` + events; `origin: quick_ask` optional).
- Autonomy chip → popover (preset summary, link to Settings → Permissions).
- Pause agent → `PATCH /api/agent/control { paused: true }`.
- Listening / Paused status pill from control + runtime.

Remove `NotificationsDrawer`; Inbox is the home for needs-you.

## 6. Today v2 (V2 / UXC-02)

### Layout (mockup)

1. Greeting + **one AURA summary sentence** (`briefing.summary` or today aggregate).
2. **Needs you** (max 3): approvals + suggestions.
3. **Now and next:** next ≤3 calendar events + active run with **Stop**.
4. **Today’s plan:** ordered tasks; **Plan my day** when plans API exists.
5. **In progress:** active goals (or omit section if none).
6. **Since you last looked:** recent activity since cursor.
7. Side: Getting started only if incomplete; connection warnings **only when broken**.

### Truth rules

- Agenda from calendar API or “Calendar is not connected” + Connect — never a hard-coded empty schedule claim.
- Briefing body from structured `sections` (R1), not only raw `text`.
- Section omitted when empty **and** there is no next action (except explicit connect/setup CTAs).
- Skeletons while loading; no permanent decorative empty cards.

### API

`GET /api/today` returns a single payload assembled in application layer:

```json
{
  "greeting": { "name": "...", "summary": "..." },
  "needs_you": [{ "kind": "approval"|"suggestion", "...": "..." }],
  "now_next": { "events": [...], "active_run": null },
  "plan": { "tasks": [...], "plan_id": null },
  "goals": [...],
  "since_last_looked": [...],
  "onboarding": { "...": "..." },
  "connections": { "warnings": [...] },
  "briefing": { "sections": [...], "text": "...", "run_id": "..." }
}
```

Supporting: `GET /api/calendar/agenda?limit=3`, `GET /api/runs/active`.

## 7. Chat v2 (V3 / UXC-04, 06)

- Left: chat list (TODAY / EARLIER) from conversations API.
- Thread: user/assistant, memory chips, step trail, **typed cards** with actions:
  - `plan` — Approve plan / Edit / Cancel
  - `approval` / pending approval stream — Approve / Edit / Deny
  - `email_draft`, `email_sent`, `calendar_event`, `calendar_proposal`, `task`, `reminder`, `receipt`, `suggestion`, `generic`
- Composer: model/runtime chip; Send; Stop when running.
- Persist/replay cards via run steps (`result_type` / `result_json`); conversation message list may link `run_id`s.

## 8. Other screens (mockup parity)

| Screen | Backend basis | Notes |
| --- | --- | --- |
| Inbox | `/api/inbox` | Open + Done; urgency merge approvals+suggestions(+selected reminders) |
| Tasks | existing tasks + reminders | Merge Reminders into Tasks views; NL add strip → chat/run |
| Goals | `/api/goals`, `/api/plans` | Success criteria, plan steps, progress |
| Routines | automations → routines | Templates, Run now, quiet hours / cap copy + enforcement |
| Activity | existing activity/runs | Human summary first; ids in drawer |
| Calendar | Google calendar + proposals | Week grid; proposal drawer |
| Mail | Google gmail list/read/draft | 3-pane; external-content flag |
| Memory | existing memory + playbooks stub | Tabs: facts, people, playbooks (playbooks CRUD if A5 slice lands) |
| Connections | existing | Fix banners when broken |
| Settings → Permissions | `/api/agent/control` | Presets, hard ceilings list, budgets |
| First-run | onboarding | Autonomy step before finish |
| Help | static + How AURA works | Map to nine things |

## 9. Backend domain additions

### 9.1 Agent control (trust surface, A4 subset)

Persist on owner profile or `agent_state` row:

- `autonomy_preset`: `ask_first` | `balanced` | `proactive` (default `ask_first`)
- `paused`: bool
- daily counters: commits, tokens, proactive_messages (reset by local date)
- caps from settings / defaults

`ToolRegistry.execute` and scheduler/routines respect `paused` and hard ceilings (email to new recipient, delete, spending, sharing, security) regardless of preset.

### 9.2 Goals and plans (A3 subset)

Entities: Goal, Plan, PlanStep with statuses. Approving a plan authorizes READ/PREPARE; COMMIT still gated. Restart resumes unfinished step.

### 9.3 Suggestions (A2 subset)

Suggestion entity with source citation; Accept → gate; Dismiss → feedback. Appear in Inbox and Today needs-you.

### 9.4 Routines (A1 subset)

Evolve automations toward Routine (name, instruction, trigger, allowlist, limits, channels, quiet hours). Keep briefing as a routine/template. Enforce quiet hours + daily proactive cap.

### 9.5 Result types

Extend tools/evals for `plan`, `suggestion`, `receipt` as those features land. UI never keyword-matches tool names.

## 10. Truth and safety (non-negotiable)

- External content remains untrusted (BR-04).
- Never claim an action without a successful tool/API result.
- Hard ceilings always need approval.
- Proactive output respects quiet hours and daily cap.
- Initiative (routines, suggestions, missions, plans) is always a real `AgentRun` through the registry.

## 11. Testing

- Unit: domain rules for goals/plans/suggestions/control; today assembler.
- Eval: new tools against real registry; contract test remains green.
- Playwright: nav at 360/768/1280; Today approve flow; quick-ask drawer; Pause blocks a routine tick in test harness.
- Offline: fake provider, temp DB, mocked Google.

## 12. Docs and ADRs

In the same branch: ADRs for today aggregate, agent control, goals/plans, suggestions/routines evolution; update README / feature-status / capabilities; update `.cursor/rules` if new hard rules appear.

## 13. Risks

| Risk | Mitigation |
| --- | --- |
| Scope spans Phases 5–7 | Ordered commits; ship incomplete agentic depth with honest empty/CTA, not mocks |
| Big-bang merge size | Keep commits atomic; CI must stay green on the branch |
| Design system fight with old fonts | Token swap first; avoid restyling twice |
| Calendar/Mail without OAuth | Connect CTAs; briefing/agenda `not_connected` |

## 14. Open points (defaults if unchanged)

- **Goals day-one:** full CRUD + simple plan executor; advanced replan/mission review can deepen post-merge.
- **Fonts:** Inter-first per mockup; drop Newsreader from shell if it conflicts.
- **Playbooks:** Memory tab UI + thin CRUD if time; else read-only placeholder that says unavailable.
- **Usability test:** after merge to `main`.

## 15. Acceptance (branch ready to merge)

- Mockup primary screens navigable with grouped shell and header chrome.
- Today v2 matches section model and truth rules.
- Chat v2 cards act on structured types.
- New APIs covered by offline tests; no spy-only tools.
- Pause and hard ceilings enforced in registry/scheduler paths.
- ADRs + status docs updated; CI green.
