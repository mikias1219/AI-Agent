# Compass transformation: audit, direction and roadmap

Status: **Phases 0–6 complete.** Owner decisions D1–D4 are recorded in section 12. S5
(CORS origin tighten) remains deferred until the owner confirms `FRONTEND_ORIGIN`.

Evidence labels used below:

- **[V]** checked directly in the source during this audit.
- **[A]** reported by a read-only audit pass and not re-checked line by line. Spot-check before acting.

Inputs: the repository at commit `6274637`, `docs/AURA_PROPOSAL.md` (source of truth), ADRs 0001–0024,
and the attached mockup board (33 screens, including "Information architecture v4", "Agent hub
overview" and "Needs you with mail replies").

---

## 1. Existing project overview

Compass is a single-owner personal agent.

- **Backend:** FastAPI modular monolith, about 18,000 lines of Python [A]. Layers: `domain`,
  `application`, `infrastructure`, `presentation`, wired in `app/container.py`. SQLite locally,
  Supabase Postgres in production, 18 Alembic migrations [A].
- **Frontend:** Next.js 15 App Router and Tailwind v4. 19 routes, client components that fetch with
  `useEffect` and `useState`, no shared cache [A].
- **Agent:** a reason-and-act loop (6 tool rounds, 90 seconds) where every tool call goes through
  `ToolRegistry.execute`: pause gate, permission check, approval gate, handler, audit [A].
- **Channels:** web dashboard, Telegram (long polling, allowlist), scheduled runs through
  `/internal/tick`.
- **Integrations:** Google (Gmail, Calendar, Drive), web search and fetch, MCP (stdio and HTTP),
  model providers (Ollama, OpenAI-compatible, Hermes, fake).
- **Deploy:** GitHub Actions runs backend, frontend and e2e jobs, then deploys Render and Vercel
  only if all three pass [V].

The safety core is the strongest part of the product. The weakest parts are that the agent takes
almost no initiative, and that several controls on screen do not change behaviour.

## 2. Feature inventory

| Feature | State | Notes |
| --- | --- | --- |
| Login, single owner account | Working | PBKDF2-SHA256, HTTP-only cookie, registration closes after the first owner [A] |
| Chat: runs, streaming, step trail, stop, typed cards, inline approval | Working | `/chat?q=` auto-sends into a new thread [V] |
| Quick ask drawer (Ctrl/Cmd K) | Working | Shares `useAgentRun` with Chat; cards render; command palette for go/ask/task [V] |
| Approvals | Working | Durable, bound to tool and argument hash, single use, edit creates a new approval, expiry [A] |
| Suggestions | Working | `suggestion_propose` tool; briefing and routines create capped proposals with citations [V] |
| Needs you (inbox) | Working | Approvals, Suggestions, Mail replies (`kind=mail_reply`), Done [V] |
| Tasks, reminders | Working | Tools, views, drawer, durable reminder delivery [A] |
| Goals and plans | Working | Approving a plan runs authorized read/prepare steps via `PlanExecutor`; commit steps stay `needs_ok` [V] |
| Routines | Working | Catalogue of five kinds seeded (briefing on; others off). Enable, schedule, run now [V] |
| Daily briefing | Working | A real agent run through the registry [A] |
| Today | Working | Aggregate endpoint, briefing fallback for the calendar |
| Calendar | Working (read) | Production returns 401 until Google is reconnected. No "find time", no proposed blocks |
| Mail | Partial | List/read real; quick filters remain client-side. Inbox triage proposes `mail_reply` drafts in Needs you [V] |
| Memory | Working | Propose then confirm, hybrid recall, secret redaction, forget all [A] |
| Skills (W1–W5) | Working, read only | Shown as Playbooks inside Memory |
| Activity | Working | Audit feed, run detail, CSV export |
| Google connection | Working | The Connections card always reads "Sample Gmail, Calendar, and Drive. Sign-in is not connected." [V] |
| Telegram connection | Working | Start, stop, verify and send-test controls on the Telegram page [V] |
| MCP servers | Working | Create, edit, delete, discover |
| Autonomy presets | **Shell only** | Stored and displayed. The permission policy is a static default and never reads the preset [V] |
| Daily budgets | Partial | Approved execute/destructive tools increment `commits_used` (cap 20, BR-09) via registry `on_commit`; proactive counter still used by scheduler; no token budget [V] |
| Pause agent | Working | Enforced in the registry [A] |
| Per-tool Allow / Ask / Block (APR-07) | Working | Settings → Permissions advanced table; ceilings block Allow on send/delete [V] |
| Undo window, learned rules, trust report (AG-TRU-03/04/06) | Partial | Balanced 10-min undo shipped (AG-TRU-04); learned rules / trust report still open [V] |
| Export my data, wipe workspace (BR-13) | Working | `/api/export` and confirmed workspace wipe in Settings → Data [V] |
| First-run wizard | Working | Profile, model (read only), connect, autonomy [A] |
| Help | Static page | The shell titles it "Settings" [V] |
| Demo workspace | Working, isolated | No link leads to `/demo` [A] |

Dead or duplicated code [A]: `features/overview/*`, `components/shell/stub-page.tsx`,
`components/shell/autonomy-chip.tsx`, `features/help/help-panel.tsx`, `components/ui/toast.tsx`
(never mounted), `HUB_ALIASES` in `nav.ts`, the unreachable mock branch in `google-page.tsx`.
Duplicate APIs: `/api/automations` and `/api/routines`; `/api/chat`, `/api/chat/stream` and `/api/runs`.

## 3. Technical audit

**Strengths**

- The registry gate is real and consistently used by chat, briefing, approvals, suggestions and the
  Hermes runtime [A].
- Approvals are durable and replay-safe [A]. Tool results are typed, so cards are not guessed.
- Domain layer is clean and guarded by import-linter [A].
- Roughly 367 backend tests, 36 eval scenarios, 77 frontend unit tests, a Playwright smoke suite.

**Weaknesses, ranked**

1. `presentation/web/app.py` is 2,049 lines: routes, request models, middleware, auth, OAuth and
   serializers in one file [A].
2. Layering is enforced only for `domain`. `application/tools/builtins/google.py` and `telegram.py`
   import infrastructure clients; the Google list routes and the Today agenda call `GoogleApiClient`
   directly, outside the registry [A].
3. The policy layer is a static default. Presets, per-tool permissions, budgets and hard ceilings
   are described in the UI and in the proposal but are not implemented [V].
4. No producer for suggestions and one routine kind: the agent is reactive [V].
5. The owner id `dashboard` is hard-coded across container, scheduler and routes; BR-01 asks for a
   real `owner_id` [A].
6. `detail=str(exc)` is used widely, so provider and storage messages can reach the client [A].
7. `Base.metadata.create_all` runs on boot next to Alembic, which can hide migration drift [A].
8. Frontend has no data layer: no cache or dedupe, the shell polls two endpoints every 3 seconds,
   and the same endpoint is fetched by several mounted components [A].
9. The Hermes runtime skips skill tool groups and the round and time limits [A].
10. The README has no status table although the workspace rule asks for one; status lives in the
    generated `docs/feature-status.md` [V].

## 4. UI and UX problems

Ranked by how much they hurt a first-time owner.

1. **Controls that do nothing.** Choosing Balanced or Proactive changes no behaviour, and the
   "commits" budget never moves. This is the visual-only pattern the brief asks to remove [V].
2. **Labels that overstate.** "Sorted by Compass" on Mail is a browser regex [V]. The Google card says
   "Sample … not connected" when it is live [V].
3. **Navigation matches neither reference.** The current shell (Today, Chat, Needs you; Spaces:
   Work, Schedule, Memory, Agent; Connections, Settings) is my consolidation from the previous
   round. The mockup's IA v4 criticises it specifically: "Spaces" is vague, Mail does not belong
   under Schedule, Memory is part of the agent, and two footer items both configure the agent.
4. **Stacked chrome.** A hub route shows a shell title, a purpose line, an eyebrow, a page title and
   then tabs. Tasks stacks four controls: hub tabs, Open/Approvals, view tabs, List/Board [A].
5. **Chat is not the centre.** Asking from Today prefills Chat without sending. Quick ask is a
   second, poorer chat. There is no command palette [A].
6. **Inconsistent page frames.** Widths vary between `max-w-3xl`, `5xl` and `6xl`, title sizes between
   `text-2xl` and `text-[26px]`, and three copies of a select style exist [A].
7. **Feedback is thin.** The toast component is never mounted, so success and undo have no home.
   Loading is a spinner everywhere; the mockup specifies skeletons [A].
8. **No mobile navigation pattern.** A slide-over sidebar only; the three-pane Mail layout has fixed
   minimum widths [A].
9. **Accessibility.** Tabs have no `tabpanel` or arrow-key handling, drawers do not trap focus [A].
10. **Help is mislabelled** as Settings in the header [V].

## 5. Product vision

Compass is a calm personal agent workspace: one place to see the day, ask for something, and decide on
what the agent prepared.

Principles, each with a concrete test:

1. **Truthful by construction.** A control exists only if it changes behaviour. A label names the
   agent only if an agent run produced the content.
2. **Conversation first.** Anything can be asked from any screen and the answer appears in place.
3. **Six destinations.** Everyday work in four, review and configuration in two.
4. **Progressive disclosure.** Everyday, then Review, then Configure, then Advanced behind a link.
5. **One home per thing.** Approvals live in Needs you; elsewhere they are references.
6. **Approval before commit.** Send, schedule, share and delete always wait, with the exact payload.
7. **Every action leaves a receipt.** What was read, what changed, how to undo it.
8. **One vocabulary.** The same sixteen status words on every screen.
9. **Safe by default.** Least privilege for tools, untrusted external content, single owner.
10. **Keyboard and phone friendly.** Command palette, bottom bar under 768 px, 44 px targets.

## 6. New information architecture

Adopt the mockup's IA v4 (subject to decision D1).

| Destination | Question it answers | Contains | Today's routes it absorbs |
| --- | --- | --- | --- |
| Today | What is my day? | Summary, needs you, now and next, plan, in progress, since you last looked | `/` |
| Chat | Ask or delegate | Threads, plan cards, approvals inline, receipts | `/chat`, quick ask |
| Needs you | What is waiting on me? | Approvals, Suggestions, Mail replies, Done | `/inbox`, part of `/mail` |
| Plan | What am I working on? | Tasks, Goals, Calendar | `/tasks`, `/goals`, `/calendar` |
| Agent | What is Compass, and what did it do? | Overview, Skills, Memory, Routines, Activity, Connections | `/memory`, `/routines`, `/activity`, `/connections/*` |
| Settings (footer) | My preferences | Profile, Appearance, Permissions, Data | `/settings`; Help moves to the profile menu |

Rules:

- Old URLs redirect, so links from Telegram and bookmarks keep working. No functionality is removed.
- One title per page. The shell header shows the destination name only; the page shows tabs and
  content. Purpose lines appear in empty states, not permanently.
- At most one tab row per page. Secondary choices become filters or a view menu.
- Mobile: bottom bar with Today, Chat, Needs you, Plan, More.
- Header: destination title, command field, bell, profile. Pause and autonomy live in Agent →
  Overview and in the profile menu.

Mail (decision D2): Compass should not be a second mail client. Mail that needs a decision appears in
Needs you with a summary and a draft. A read-only list of all mail stays reachable from that tab.

## 7. Design system

Taken from the mockup's App shell, Components and Color usage pages, mapped onto the existing
`styles/tokens.css` variables.

- **Grid:** 8 px. Page padding 32, card padding 16, row height at least 48 (compact 36), content
  width 1120, chat text width 720, detail drawer 340.
- **Type (Inter):** Display 30, Title 18, Body 14, Small 13, Caption 12. No other sizes.
- **Colour:** accent `#0F766E`, success `#15803D`, warning `#B45309`, danger `#B42318`, info `#1D4ED8`,
  with light and dark values as tokens. No hex values in feature code.
- **Rules:** one primary button per card; buttons are named for the action; every chip has a word,
  never colour alone; destructive actions are red and say what is lost.
- **Status words:** Pending, Approved, Denied, Expired, Done, Failed, Needs you, Verified, Late,
  Running, Scheduled, Proposed, Listening, Needs setup, Error, Paused.
- **Access classes shown to the owner:** Read, Prepare, Commit (the code's `execute` and
  `destructive`).
- **Components to add or finish:** `PageFrame`, `Select`, `Banner`, `Skeleton`, accessible `Tabs` with
  panels, focus-trapped `Drawer` and `Modal`, mounted `Toast` with Undo and Retry, `CommandPalette`,
  one `Row` family for approval, suggestion, task, goal, routine, memory, connection and activity.
- **States:** skeleton while loading, an empty state with one next action, an error state with
  "Try again". Lists over 20 rows paginate and show the range.

## 8. Feature gap analysis

Each gap: what is missing, why it matters, expected behaviour, changes, safety.

**G1. Suggestions have no producer.**
Why: the agent never takes initiative, and half of Needs you is permanently empty.
Expected: routines and the briefing run propose at most a few suggestions per day, each citing its
source, ranked, respecting quiet hours and the daily cap.
Changes: backend, a `suggestion_propose` prepare tool registered in the registry and used by
routine runs; eval scenario. Frontend, none beyond the existing rows. Database, none.
Safety: a suggestion is a proposal only; accepting one still passes the approval gate.

**G2. Mail triage is a browser regex.**
Why: the label claims agent work that did not happen.
Expected: an "Inbox triage" routine reads recent mail, classifies it, summarises, and drafts replies
for the ones that need an answer. They appear under Needs you → Mail replies with Approve and send,
Edit, Dismiss, Create task, Snooze.
Changes: backend, a triage routine as a real agent run, stored triage results; one migration for a
small `mail_triage` table or reuse of suggestions with `kind=mail_reply` (preferred, no new table).
Frontend, the Mail replies tab and detail panel. Until this ships, rename the current rail to
"Quick filters".
Safety: email bodies are untrusted and wrapped; sending always needs approval (BR-05).

**G3. Only one routine, and none can be created.**
Why: the Routines screen is a single row.
Expected: a small catalogue (morning briefing, inbox triage, evening wrap-up, weekly review, deadline
guard) that the owner turns on and schedules. No free-form builder in this round.
Changes: backend, routine kinds beyond `daily_briefing`, each a prompt plus allowed tool groups;
generalise the scheduler job handler. Database, no new table, new `kind` values.
Safety: BR-14, routine runs use the same gate and cannot commit without approval.

**G4. Approving a plan does not run it.**
Why: W6 "Reach a goal" stops at step 3.
Expected: approved read and prepare steps run in order, commit steps raise approvals, progress shows
on the goal.
Changes: backend, a plan step executor through the registry. Frontend, step status on the goal page.
Safety: plan approval authorises read and prepare only (already encoded in `domain/goals.py`).

**G5. Autonomy presets and budgets are cosmetic.**
Why: a trust control that does nothing is worse than none.
Expected, step one: copy says exactly what is true today (every send or change asks, in every mode)
and the commit counter counts real approved commits against the BR-09 cap of 20.
Expected, step two (decision D3): Balanced lets a short list of reversible actions on the owner's own
data run with a 10-minute undo.
Changes: backend, policy reads agent control; registry increments the counter; hard-ceiling checks
(new recipient, delete, share, guests) evaluated before any preset. Frontend, Agent → Overview.
Safety: ceilings first, presets second; email is never automatic.

**G6. Per-tool permissions (APR-07).** Missing. Allow, Ask or Block per capability, stored on the
owner profile, read by the policy. Send cannot be set to Allow. Behind an "Advanced" link.

**G7. Agent overview.** No single place shows status, autonomy, limits, capabilities and recent
work. All of the data already exists in `/api/status`, `/api/agent/control`, `/api/agent/skills`
and `/api/activity`; this is mainly a screen, plus a small read-only capabilities endpoint derived
from the registry.

**G8. Chat as the centre.** Send `?q=` automatically, share one run-stream hook between Chat and
quick ask, show cards in quick ask, add a command palette (new task, go to, ask).

**G9. Export and wipe (BR-13).** Missing. A data export and a confirmed workspace wipe in Settings →
Data. Wipe is destructive and needs the typed-phrase confirmation already used for memories.

**G10. Telegram controls.** Expose the existing start, stop and verify endpoints, plus "Send test
message", in Agent → Connections.

## 9. Security assessment

Severities are for the deployed, single-owner product.

| ID | Severity | Finding | Fix |
| --- | --- | --- | --- |
| S1 | High | Google OAuth `state` is the constant `ro=0` or `ro=1`, and `/api/google/callback` is public. Anyone who can obtain an authorisation code for this OAuth client can replace the workspace's Google account without logging in. Limited while the Google app is in Testing mode with only the owner as a test user [V] | Random state bound to the session, verified in the callback; require a session on the callback; add PKCE |
| S2 | High | MCP stdio transport starts any command the API receives as a subprocess with the full server environment. A stolen session becomes code execution on the API host [V] | Disable stdio in production unless an explicit environment flag is set; pass a minimal environment (decision D4) |
| S3 | High | An MCP server marked read-only registers every one of its tools as `read`, so a tool that changes things runs with no approval [V] | Default every MCP tool to `execute`; allow `read` per tool only |
| S4 | Medium | MCP HTTP URLs are not checked against private and metadata addresses, unlike `web_fetch` [A] | Reuse the web denylist |
| S5 | Low (deferred) | The browser-origin allowlist accepts any `https://personal-ai-agent*.vercel.app`. Cookie is SameSite=Lax and host-scoped, so impact is limited. Removing the regex without confirming `FRONTEND_ORIGIN` can lock the owner out [V] | Confirm `FRONTEND_ORIGIN`, then allow only configured origins |
| S6 | Medium | Done | AES-256-GCM (`v2gcm:`) with migrate-on-read from legacy XOR+HMAC [V] |
| S7 | Medium | `/internal/tick` falls back to the session signing key as its secret [V] | Require a separate secret in production |
| S8 | Medium | Done | Per-owner rate limit on chat/runs/MCP + MAX_CONCURRENT_RUNS [V] |
| S9 | Low | Done | Public `/api/health` is liveness only; details require session [V] |
| S10 | Low | Done | Activity CSV prefixes formula-like cells [V] |
| S11 | Low | Done | Login lockout persisted under data/login_lockout.json [V] |
| S12 | Low | Done | Next.js + FastAPI security headers (CSP, Referrer-Policy, HSTS in prod) [V] |
| S13 | Info | Hard ceilings are stricter than specified today because every commit asks. The gap opens only when presets become real (G5) [V] | Implement ceilings before presets |

Confirmed good [A unless marked]: password hashing, session cookie flags, global auth middleware
[V], approval binding and single use, pause gate, untrusted flag carried into later approvals,
Telegram allowlist and private-chat-only approval, web fetch denylist, memory secret redaction,
no secrets tracked in git, no raw HTML rendering of model output.

## 10. Implementation roadmap

Each phase ships with tests, an ADR for its decisions and a passing CI run.

| Phase | Content | Size |
| --- | --- | --- |
| 0. Repair and secure | S1, S2, S3, S4, S5, S7. Fix the labels that overstate (Google card, "Sorted by Compass", Help title, preset copy). Delete dead code. ADR for the shell decision | Small |
| 1. Shell and design system | Six destinations with redirects, one title per page, bottom bar, tokens and type scale, `PageFrame`, `Tabs`, `Select`, `Banner`, `Skeleton`, `Toast`, focus traps. Playwright updated | Medium |
| 2. Everyday screens | Today v2, Chat as centre (G8), Needs you with Approvals, Suggestions, Done | Medium |
| 3. Agent hub | Overview (G7), Skills, Memory, Routines, Activity, Connections with Telegram controls (G10), real commit counter (G5 step one) | Medium |
| 4. Initiative | Suggestion producer (G1), routine catalogue (G3), mail triage and Mail replies (G2), plan executor (G4) | Large |
| 5. Trust and data | Per-tool permissions (G6), hard ceilings and Balanced with undo (G5 step two), export and wipe (G9), S6, S8–S12 | Large |
| 6. Hardening | Split `app.py` into routers, extend import-linter to all layers, frontend data layer, accessibility pass, full QA | Medium |

## 11. Completed improvements

- `46de228` Today: provider errors no longer shown in the greeting, formatted briefing times, calendar
  fallback from the latest briefing, stale run banner removed, Memory tab deep link, unsafe tool
  names filtered, stale Google token now reports "reconnect".
- `6274637` Shell: nine destinations with hubs for Work, Schedule and Agent. Superseded by ADR-0026.
- Phase 0 (uncommitted): signed Google OAuth state (S1); MCP stdio off in production unless
  `MCP_ALLOW_STDIO`, private URLs blocked, tools default to `execute` unless `readOnlyHint` (S2–S4);
  dedicated `INTERNAL_TICK_SECRET` in production (S7); MCP tool refresh uses `mcp_` prefix; truthful
  labels for Google card, mail quick filters, autonomy presets, MCP copy; dead overview/stub/sample
  code removed. ADR-0025. S5 deferred.
- Phase 1 (uncommitted): six-destination nav, Plan / Needs you / Agent hubs, mobile bottom bar,
  design tokens, `PageFrame`, Tabs with panels and arrows, `Select`, `Banner`, `Skeleton`, mounted
  Toast, focus-trapped Drawer/Modal. ADR-0026.
- Phase 2 (uncommitted): Chat `?q=` auto-sends into a new thread; shared `useAgentRun` powers Quick
  ask with the same cards; Ctrl/Cmd+K command palette (ask, new task, go to); Needs you tabs are
  Approvals / Suggestions / Done with an honest empty state for suggestions; Today drops the
  duplicate destination eyebrow.
- Phase 3 (uncommitted): Agent → Overview at `/agent` (status, pause, autonomy label, live
  capabilities from `/api/agent/capabilities`, today's commit and proactive limits, recent
  activity); registry `on_commit` bumps `commits_used` after successful approved execute/destructive
  tools (cap 20); Telegram Controls (verify / start / stop / send test); Settings permissions show
  the real commit counter. ADR-0027.
- Phase 4 (uncommitted): `suggestion_propose` prepare tool; briefing follow-up suggestions;
  routine catalogue (inbox triage, evening wrap-up, weekly review, deadline guard) with generic
  scheduler dispatch; Mail replies tab; plan step executor after approve. ADR-0028.
- Phase 5 (uncommitted): workspace export + wipe (BR-13); OwnerPermissionPolicy with
  per-tool Allow/Ask/Block, hard ceilings (APR-07), Balanced undo (AG-TRU-04), S6 token
  encryption, and S8–S12 hardening. ADR-0029, ADR-0030, ADR-0032 (S6).
- Phase 6 (uncommitted): `presentation/web/routers/` for agent, workspace, auth, tasks, goals,
  runs/chat, Google, integrations, memory, today/inbox; import-linter for application layers;
  frontend GET cache/dedupe (`lib/client-cache`) + `usePolling`; skip link and tab panels.
  ADR-0031.

## 12. Remaining work and open decisions

Decisions (answered):

- **D1.** Six destinations (Today, Chat, Needs you, Plan, Agent, Settings). ADR-0026.
- **D2.** Mail replies in Needs you with summary and draft; read-only list one click away. List tab
  ships now; replies with drafts arrive with G2.
- **D3.** Truthful copy first; later Balanced with a 10-minute undo for reversible actions on own
  data; email never sends automatically.
- **D4.** Stdio off in production unless `MCP_ALLOW_STDIO=1`; HTTP MCP keeps working.

Still open for the owner:

- Confirm `FRONTEND_ORIGIN` before tightening CORS (S5).
- Set repository secret `INTERNAL_TICK_SECRET` (different from `DASHBOARD_SECRET_KEY`) before deploy.
- Reconnect Google in production; rotate the production password that was pasted into chat.
- Mockup HTML at the repository root stays untracked.

Phase 6 complete. Remaining owner ops: confirm `FRONTEND_ORIGIN` (S5), set
`INTERNAL_TICK_SECRET`, reconnect Google / rotate pasted password, full QA when ready.
