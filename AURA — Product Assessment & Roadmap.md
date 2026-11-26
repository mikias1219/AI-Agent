# Compass — Product Assessment & Roadmap

Nov 26, 2026 · @mikias

## 1. Executive summary

Compass is a solid, security-minded AI assistant with a good task and learning core, but it is not yet a personal life operating system. Its time, task and calendar views disagree with each other. It has no finance, habit, project or recurrence model. Its scheduler is too unreliable for 5 AM routines.

**Maturity:** late beta for "AI chief of staff"; early alpha for "personal life OS". Across 21 frontend routes and 140+ API endpoints there are 25 SQLAlchemy tables and 22 migrations. Backend tests: 798 passed; frontend unit tests: 128 passed; TypeScript check clean.

**Strengths**

- Safety architecture is above average for a personal project. Every agent tool declares read / prepare / execute / destructive. Execute and destructive pause for durable approval. External content is labelled untrusted, and every run is audited.
- Sound security basics: PBKDF2 passwords (310k rounds), Google tokens encrypted with AES-256-GCM, login lockout after 5 failures, CSRF origin checks, strict CSP, and confirmation phrases for wipe and forget-all.
- Clean modular monolith (domain / application / infrastructure / presentation) with an import linter, ADRs and a generated feature-status file.
- Useful life modules already work end to end: day planning with carry-over and outcome scoring, spaced-repetition vocabulary, reading plans, diary with streaks, notes, files, goals with plans.

**Biggest weaknesses**

1. **Two date models for tasks.** Today's task list reads `due_at` while the Plan day view and day score read `plan_date`. Tasks planned for today never appear in Today's list, and 9 overdue tasks are invisible on Today (verified).
2. **Agent tool routing is blind.** When no skill matches, a fast model picks tool groups without seeing the user's message. Tools such as `learn_save_items` silently disappear. This is why chat said "the Learn-saving tool isn't available" (verified in code).
3. **Identity and settings disagree.** Account name ("Dersso") and profile name ("mikias") are separate fields. Notification times and routine schedules are partly separate, so they drift.
4. **No personal finance at all.** No income, expense, budget, recurring-bill or savings entities, endpoints, tools or screens.
5. **No habits, recurrence, projects, dependencies or time tracking.** Daily routines such as prayer, exercise and Bible reading must be re-created by hand each day.
6. **Unreliable timing.** The scheduler is driven by a GitHub Actions cron every 5 minutes, hitting a Render free instance that sleeps. Reminders and briefings can be late by minutes to an hour, and first loads take 5–10 s or more.

**Major risks**

- **Trust:** contradictory numbers ("Compass did 94 things" vs "0 runs finished"; "0 of 0 tasks" vs 9 overdue) teach the user not to rely on the dashboard.
- **Data integrity:** no foreign keys from owner columns to accounts, statuses stored as free strings, unknown request fields silently dropped (a `recurrence` value is accepted and discarded).
- **Finance safety:** once money arrives, the current approval model needs a dedicated "financial write" access kind. Today a `prepare` tool writes without asking.

**Recommendation:** fix the P0 consistency bugs and scheduler reliability first (about 2 weeks). Then add a unified Habits + Recurrence foundation, then the Finance module on top of it. Finance and habits both need recurrence, so building it once avoids two designs.

## 2. Existing feature inventory

Of 29 features examined, 12 work end to end, 11 are partial, inconsistent or broken, 4 core life-OS areas are missing, and 2 could not be verified. "Verified" means it was exercised on the live site or against a local copy, not just seen in the UI.

| Area | Feature | Status | Evidence |
| --- | --- | --- | --- |
| Auth | Single-owner register, login, logout, lockout | Works | Local: 2nd registration 409, 5 bad logins then 429, cross-origin POST 403 |
| Auth | Session lifetime and revocation | Partial | 12 h stateless HMAC cookie; logout only deletes the cookie (`routers/_common.py`, `routers/auth.py`) |
| Profile | Name, bio, birthday, photo, timezone | Inconsistent | Account name and profile name are separate fields: live UI shows "Dersso" then "mikias" |
| Today | Greeting, briefing, day cards, needs-you, agenda, notes | Partial | Task list reads `due_at` only (`today_service._plan_tasks`); overdue tasks never shown |
| Today | Briefing text | Partial | Raw markdown (`**Daily Briefing**`) and truncation on the live site |
| Chat | Streaming chat, history, step trail, stop | Works | Live: answered "What should I focus on today?" in about 20 s using calendar and tasks |
| Chat | Tool result cards | Partial | Falls back to raw tool output, so JSON shows (`chat-cards-logic.ts` `cardsFromSteps`) |
| Chat | Learn hand-off from Learn page | Broken | Live: prompt lost after reload; agent said Learn tool unavailable |
| Tasks | Create, edit, complete with outcome, reopen, soft delete | Works | Local: validation for empty/long title, bad priority, negative actual |
| Tasks | Day planning and carry-over | Works | Local: carry-over moved 2 tasks; second call moved 0 (idempotent) |
| Tasks | List/board views, overdue, done | Works | Live |
| Tasks | Undo after delete | Partial | Local: `GET /api/undo` empty after UI-route delete; undo exists only for agent actions |
| Tasks | Recurrence, projects, subtasks, dependencies, timers | Missing | Not in `TaskRow`; unknown fields silently dropped |
| Calendar | Google Calendar list and create | Partial | Today's list starts at "now" (`clients.list_calendar` timeMin=now), hiding earlier events |
| Mail | Gmail triage and draft replies | Not verified | Hidden `/mail` route; needs Google on a test account |
| Inbox | Approvals, suggestions, mail replies | Partial | Opens on empty tab; duplicate suggestions for the same task |
| Goals | Goals with plans and plan executor | Works (basic) | No numeric target or progress % |
| Learn | Vocabulary with spaced review (Leitner boxes) | Works | Local: add, review "know/again", stats; duplicates skipped silently |
| Reading | Plans from templates, logs, streak | Works | Local; templates are Bible-focused only |
| Library | Notes, diary (one per day), files 5 MB | Works | Local: empty note rejected; second diary entry same day 409 |
| Routines | Briefing, wrap-ups, triage, deadline guard, nudges | Partial | Two overlapping wrap-ups (`daily_wrapup` 21:00 and `evening_wrapup` 18:00) |
| Agent | Memory with proposals, forget-all | Works | Not deeply tested |
| Agent | Autonomy presets, pause, daily commit caps | Works | Live UI; "Proactive" is labelled "not active yet" |
| Agent | Trust report and activity | Inconsistent | Trust report says 0 runs; Today says 94 things this week |
| Integrations | Telegram, MCP, web search/fetch, Drive backup | Not verified | Need live credentials |
| Data | Export JSON, wipe with phrase | Works | Local: export 10 KB with 18 sections; wipe needs token + phrase |
| Finance | Income, expenses, budgets, bills, savings | Missing | `GET /api/expenses` etc. return 404; no tables |
| Habits | Habit check-ins and streaks | Missing | No entity |
| Time | Time tracking and productivity analytics | Missing | Only daily score and week/month rate (`/api/days/stats`) |

Hidden but present routes: `/mail`, `/help`, `/memory`, `/goals`, `/activity`, `/calendar`, `/routines`, `/connections`. Most are reached as tabs, but `/mail` and `/help` are hard to discover.

## 3. End-to-end testing report

The morning and evening routines fail as a whole even though most single actions pass. The user cannot see one trustworthy picture of today. Tests ran three ways: the live site (read-only plus two chat prompts), an isolated local copy with test data (SQLite, offline model), and the existing automated suites.

**Automated suites (executed):** backend `pytest` 798 passed, 0 failed (2 min 32 s); frontend `vitest` 128 passed in 21 files; `tsc --noEmit` clean. Playwright e2e and live-model evals were not run (no browser target or model key).

### Scenario A — Morning routine (5:00 AM)

| Step | Expected | Actual | Result |
| --- | --- | --- | --- |
| View today's schedule | All of today's events, including 5:00–6:15 | Calendar tab lists events from "now" onward; at 07:54 the 5:00 prayer, 5:20 Bible reading, 5:50 exercise and 6:15 shower were missing | Fail |
| See daily priorities | Today shows tasks planned or due today | Today's task list is empty when tasks are planned with `plan_date` (local: 8 planned, list empty) | Fail |
| Review unfinished tasks from yesterday | Overdue and yesterday's leftovers on Today | Live: "0 of 0, nothing planned" while Plan → Overdue has 9 tasks incl. 2 × P1 | Fail |
| Carry yesterday's work forward | One action moves leftovers to today | Works via API (`POST /api/days/{day}/carry-over`, idempotent); not offered on Today | Partial |
| Track morning habits (prayer, exercise, Bible, learning) | Tick habits, see streaks | No habit model; must be daily tasks re-created by hand | Fail |
| Record exercise with a target | Planned 30 min, did 35 | Works: outcome + actual value stored, score updated | Pass |
| Log Bible reading | Log reference + reflection | Works (`POST /api/reading/logs`) | Pass |
| Check reminders | Reminder list on Today | Reminders exist only as agent tools; no reminder view | Fail |
| Ask for a daily briefing | Fresh briefing in chat | Live: good answer in about 20 s, but raw JSON receipt cards below it | Partial |

### Scenario B — Daily productivity

| Step | Expected | Actual | Result |
| --- | --- | --- | --- |
| Create task with priority and date | Saved, shown in Today and Plan | Saved; shows in Plan, not in Today's list | Partial |
| Validation | Bad input rejected | Empty title, 257-char title, bad priority, negative actual all 422 | Pass |
| Organise into projects | Project entity with progress | Free-text `project` string only | Fail |
| Dependencies / subtasks | Blocked-by links | Not modelled | Fail |
| Recurring work (weekly report) | Recurs automatically | `recurrence` field accepted (201) and silently dropped | Fail |
| Complete with partial outcome | Stored with note | Works with `partial` (UI says "Partly") | Pass |
| Delete then undo | Undo offered | Soft delete works; `GET /api/undo` empty for UI deletes | Partial |
| Track time spent | Timer or log | Not available | Fail |
| Review daily productivity | Score and trend | `/api/days/stats`: streak, week and month rate only | Partial |

### Scenario C — Learning and development

| Step | Expected | Actual | Result |
| --- | --- | --- | --- |
| Ask Compass to teach 5 words and save them | Words saved to Learn | Live: words taught but not saved; agent said tool unavailable | Fail |
| Add a word manually | Saved | Works; case-insensitive duplicates skipped | Pass |
| Duplicate feedback | "Already saved" message | Returns 201 with an empty list, no message | Partial |
| Spaced review | Box moves, next review set | Works with `know` / `again` | Pass |
| Study plan with milestones and % | Course or plan progress | Goals + plan steps only; no % or milestones | Fail |
| Certifications, courses | Tracked | Not modelled | Fail |

### Scenario D — Evening review

| Step | Expected | Actual | Result |
| --- | --- | --- | --- |
| Review completed vs unfinished | Day summary | Day view shows done/planned and score | Pass |
| Why goals were missed | Outcome notes summarised | Outcome note stored; no "why" analysis on screen | Partial |
| Review habits | Habit grid | No habits | Fail |
| Review daily spending | Spend vs budget | No finance | Fail |
| Tomorrow's schedule | Tomorrow's events and tasks | Plan day view can step to tomorrow | Pass |
| Diary entry | One entry, more appended | Second POST same day 409; UI must offer "add more" | Pass (UI handles) |
| AI performance summary | Wrap-up message | Two overlapping wrap-up routines; time setting edits only one | Partial |

### Security and negative tests (local)

| Test | Result |
| --- | --- |
| Protected endpoint without session → 401 | Pass |
| Weak password (<8 chars) → 422 | Pass |
| Second owner registration → 409 | Pass |
| Cross-origin POST with valid cookie → 403 | Pass |
| 5 wrong passwords → then 429 lockout | Pass |
| Wipe / forget-all without token + phrase → 422 | Pass |
| Invalid timezone → 400 | Pass |
| Session unusable after logout | Pass for this client; the token itself stays valid for 12 h if copied (stateless) |

### Live-site defects (observed on production, read-only)

- "Dersso" shown for 3–6 s on every page load, then "mikias".
- Today: skeletons for 5–10 s; `/api/today` pending while Render wakes; activity fetched as 3 × 200 rows.
- Needs you badge 4, but the page opens on an empty Approvals tab.
- Notification drawer lists "Telegram · runtime" and "Scheduler · tick" system events.
- Default black Next.js 404 for unknown routes.

## 4. UI/UX audit

The visual design is clean and calm; the problem is information architecture. The same day is split across Today, Plan, Calendar, Needs you and Agent, and each shows different numbers. Fix the structure before the styling.

### Cross-cutting issues

| Problem | Why it matters | Change |
| --- | --- | --- |
| Numbers disagree between screens | The user stops trusting every number | One `DaySnapshot` service feeds Today, Plan and the agent |
| Developer details exposed (model ids, OAuth scopes, "Commit: 14", tool sources, `briefing:tasks`) | Cognitive load, looks unfinished | Move to a "Technical details" disclosure in Agent → Overview |
| Long skeleton waits, no progress feedback | Feels broken at 5 AM | Server-render the shell; cache the last snapshot and refresh in the background |
| Sidebar has a horizontal scrollbar (content 279 px in a 219 px box) | Visual noise | Fix overflow in `dashboard-layout.tsx` |
| 404 page is the default black Next.js page | Breaks the theme, no way back | Add `app/not-found.tsx` with the app shell and a Today link |
| US date format (11/25/2026) for an Addis Ababa user | Misreading dates | Format from profile language + timezone via one `formatDate` helper |
| Mobile not verified | Most quick capture happens on a phone | Responsive pass + bottom tab bar under 768 px (see layout below) |

### Today

- **Wrong:** five stacked sections (briefing, ask box, 4 day cards, needs you, agenda, notes) with no single "what now". The briefing is raw markdown and truncated. Overdue work is absent.
- **Effect:** the user scans everything and still does not know the next action.
- **Improved layout (top to bottom):** 1) a header with greeting, date and a one-line AI summary. 2) A **Now / Next** strip: current or next event plus top 3 tasks, overdue badge, one-tap "carry over". 3) A **Habits row** of tappable chips (prayer, exercise, Bible, English). 4) A **Money row**: spent today, left in this month's budget, next bill. 5) A collapsible full agenda. Move "Recent notes" to Library.
- **Reuse:** `DayCard`, the inbox item component and the command palette. The ask box becomes the global quick-capture (task, expense, note, habit).

### Chat

- **Wrong:** raw JSON receipts; generic titles ("Chat on Nov 25" × 6); the model string in the header; a hand-off from Learn can lose the prompt.
- **Change:** render a short human summary per tool, with raw output behind "details". Auto-title chats from the first message. Show a toast when a hand-off fails. Show approval cards inline with clear Approve / Edit / Reject.

### Plan (Tasks, Goals, Calendar)

- **Wrong:** three tab rows (Tasks/Goals/Calendar, then Day/Upcoming/Overdue/All/Done/Approvals, then List/Board). An Approvals tab duplicates Needs you. Overdue has no count. Every due date reads "Nov 12, 9:00 AM".
- **Change:** one row of views with counts (Today 6 · Overdue 9 · Upcoming · Done). Remove Approvals from Plan. Show the time block from the task, not a default 9:00. Add bulk actions for overdue: move to today, reschedule, drop.

### Needs you

- **Wrong:** opens on the empty Approvals tab while 4 items wait under Suggestions; duplicate suggestions for one task; unclear "Accept".
- **Change:** open on the first non-empty tab; show counts on tabs; merge duplicates by `source_ref`. Rename actions to what they do ("Move to today", "Mark done", "Dismiss for a week").

### Learn and Library

- **Good:** clear empty states and validation.
- **Change:** show "Already in your list" on duplicate words. Add courses and certifications as goal templates with a progress bar. Add reading templates beyond Bible plans (books, articles).

### Agent and Settings

- **Wrong:** five tabs mixing user concepts (Memory, Routines) with operator data (capabilities, trust report). Routine names are inconsistent ("daily wrapup" vs "Evening wrap-up"), and two wrap-ups overlap. The notification time edits only one routine. Time zone is free text.
- **Change:** Settings → "Routines & reminders" owns every schedule in one list. Agent keeps Memory, Activity and Connections. Use a time zone picker. Show empty-state copy on the trust report instead of dashes.

### Mobile layout (proposed)

Under 768 px: a bottom bar with Today, Plan, a centred **+** quick-add (task / expense / habit / note), Money and Chat. Drawers become full-height sheets. Tables become cards.

## 5. Missing feature analysis

Eight capabilities are missing for a complete personal life OS. Three of them (recurrence, habits, finance) block the daily routine you described, and all three share one recurrence engine.

| Missing capability | Why it is essential | Builds on | Priority |
| --- | --- | --- | --- |
| **Recurrence engine** (RRULE: daily, weekly, monthly, quarterly, yearly; start/end; exceptions) | Prayer, exercise, rent, salary and weekly reports all repeat | New `recurrence_rules` table used by tasks, habits, bills and income | P1 |
| **Habits** (check-in, target per day/week, streak, skip with reason) | Morning routine is mostly habits, not tasks | Recurrence engine; reuse day score | P1 |
| **Personal finance** (income, expenses, budgets, bills, savings goals) | Requested core module; nothing exists | Recurrence engine; Section 6 | P1 |
| **Projects** as entities (status, owner, deadline, progress %, budget link) | `project` is a free-text string today | Tasks; finance project budgets | P2 |
| **Subtasks and dependencies** (`parent_id`, `blocked_by`) | Real work has steps and blockers | Tasks | P2 |
| **Time tracking** (start/stop, manual entries, per project) | "Where did my day go?" cannot be answered | Tasks, projects | P2 |
| **Learning paths** (course, certification, milestones, % complete, study hours) | Learning is a stated priority; only words and Bible plans exist | Goals + time tracking | P2 |
| **Weekly / monthly review and analytics** | Needed to answer "am I improving?" | All modules via one analytics service | P2 |

Smaller gaps worth adding: a reminder list on Today; a quick-capture parser ("lunch 250 cash" → expense; "pray 5am daily" → habit); health metrics (sleep, weight, water) as optional habit types; and an offline-capable PWA for phone use.

**Do not duplicate:** goals and plans, the day score, reading streaks and routines already exist. New modules should plug into them (for example a habit check-in can count toward the day score; a savings goal is a Goal with a money target), not create parallel versions.

## 6. Personal finance module specification

Finance is built as a ledger of real transactions plus a schedule of expected ones, never mixing the two. Expected items (salary due, rent due) become real transactions only when the user confirms them. Amounts are stored as integers in the smallest unit (santim) with a currency code; the default currency is ETB.

### 6.1 Requirements

1. Record income and expenses with amount, date/time, category and subcategory, account/payment method, merchant or payer, notes, receipt, linked budget and status.
2. Distinguish **expected** (scheduled, not yet happened) from **actual** (money moved). Statuses: `expected`, `received`/`paid`, `partial`, `overdue`, `skipped`.
3. Recurring obligations and income with daily, weekly, monthly, quarterly or yearly rules, start/end dates and due-day.
4. Editing a recurring rule changes only future occurrences; history is never rewritten.
5. Budgets: monthly, weekly, category, project, savings, emergency and special-purpose.
6. Savings goals with target, target date, monthly contribution, contribution history and projected completion.
7. Expense entry in under 5 seconds: amount + category minimum, everything else defaulted.
8. All money writes by the AI agent require confirmation.

### 6.2 Core workflows

1. **Quick expense:** tap **+** → type `250` → pick a category chip (last 6 used shown first) → Save. Defaults: now, default account, cash. Optional: merchant, note, receipt photo.
2. **Natural-language capture:** "lunch 250 cash at Kaldi's" in the ask box → parsed preview card → one tap to save.
3. **Salary day:** on the expected date Today shows "Salary 35,000 ETB expected" → Mark received (amount editable for deductions) → actual income created and linked to the occurrence.
4. **Bill due:** 3 days before, rent appears in Needs you → Mark paid (full or partial) or Snooze → overdue the day after the due date.
5. **Monthly budget setup:** copy last month or use a template → adjust category amounts → the system shows unallocated money live.
6. **Month close:** on the 1st, a review card shows planned vs actual, savings rate, top 3 overspends and the AI's suggestions for next month.

### 6.3 Data model

| Entity | Key fields | Notes |
| --- | --- | --- |
| `fin_accounts` | id, owner\_id, name, type (cash, bank, mobile money, card), currency, opening\_balance, archived | Telebirr, CBE, cash wallet |
| `fin_categories` | id, owner\_id, parent\_id, name, kind (income/expense), icon, is\_fixed | Seeded with the 14 expense categories you listed + income sources |
| `fin_transactions` | id, owner\_id, account\_id, category\_id, kind (income, expense, transfer), amount\_minor, currency, occurred\_at, status, merchant, note, budget\_id, project\_id, occurrence\_id, receipt\_file\_id, created\_by (user/agent), approval\_id | Actual money only; soft delete; immutable audit columns |
| `fin_recurring_rules` | id, owner\_id, kind, title, amount\_minor, category\_id, account\_id, rrule, start\_date, end\_date, due\_day, remind\_days\_before, version, active | Editing creates a new version from the next occurrence |
| `fin_occurrences` | id, rule\_id, rule\_version, due\_date, expected\_minor, status (expected, paid, partial, overdue, skipped), paid\_minor | Generated 90 days ahead by the scheduler; unique (rule\_id, due\_date) |
| `fin_budgets` | id, owner\_id, name, type (monthly, weekly, category, project, savings, emergency, special), period\_start, period\_end, income\_plan\_minor, rollover | One active monthly budget per period |
| `fin_budget_lines` | id, budget\_id, category\_id, planned\_minor, alert\_at\_pct (default 80) | Unique (budget\_id, category\_id) |
| `fin_savings_goals` | id, owner\_id, goal\_id (link to existing Goals), target\_minor, target\_date, monthly\_contribution\_minor, account\_id | Reuses the Goals module |
| `fin_contributions` | id, savings\_goal\_id, transaction\_id, amount\_minor, contributed\_on | Contribution history |

Constraints: `amount_minor > 0` (direction comes from `kind`); FK on every reference; `CHECK` on status and kind; currency fixed per account; transfers stored as two linked rows so balances always reconcile.

### 6.4 API

| Method and path | Purpose |
| --- | --- |
| `GET/POST /api/finance/transactions`, `PATCH/DELETE /api/finance/transactions/{id}` | Ledger with filters (period, category, account, status, text) |
| `POST /api/finance/transactions/quick` | Minimal body `{amount, category_id}`; returns the saved row in one round trip |
| `POST /api/finance/parse` | Natural-language text → draft transaction (never saves) |
| `GET/POST /api/finance/recurring`, `PATCH /api/finance/recurring/{id}` (creates a new version) | Recurring income and bills |
| `GET /api/finance/occurrences?from&to`, `POST /api/finance/occurrences/{id}/settle` | Upcoming items; settle as paid, partial or skipped |
| `GET/POST /api/finance/budgets`, `PUT /api/finance/budgets/{id}/lines`, `POST /api/finance/budgets/{id}/copy` | Budgets |
| `GET/POST /api/finance/savings-goals`, `POST /api/finance/savings-goals/{id}/contributions` | Savings |
| `GET /api/finance/summary?period=2026-11` | Dashboard numbers computed server-side |
| \`GET /api/finance/reports/{monthly | category |
| `GET/POST /api/finance/accounts`, `/categories` | Setup |

All write endpoints use typed Pydantic models with `extra="forbid"`, so unknown fields are rejected instead of silently dropped.

### 6.5 Calculations

For a budget period, with actual expenses A, planned P and actual income I:

```latex
\text{Remaining}_c = P_c - A_c \qquad \text{Utilisation}_c = \frac{A_c}{P_c}\times 100
```

```latex
\text{Expected end balance} = \text{Balance}_{now} + \sum \text{expected income} - \sum \text{unpaid bills} - \text{Avg daily variable spend} \times \text{days left}
```

```latex
\text{Savings rate} = \frac{I - A_{\text{non-savings}}}{I}\times 100
```

Rules: transfers to a savings account count as savings, not expenses. Status colours: under 80% green, 80–100% amber, over 100% red. Overspend = max(0, A − P). Average daily variable spend uses the last 30 days of non-fixed categories.

**Worked example (your sample budget):** income 35,000 ETB; planned 35,000 ETB (rent 7,500, household and food 8,000, transport 2,000, internet and mobile 1,000, personal 2,000, learning 1,500, savings 10,000, emergency 3,000). If by the 20th food spending is 6,900, utilisation is 86% (amber alert). Planned savings rate is (10,000 + 3,000) / 35,000 = 37%.

### 6.6 Recurring logic

- A daily scheduler job generates occurrences 90 days ahead (idempotent via the unique key) and marks overdue at end of due day in the owner's timezone.
- Settling creates the actual transaction and links it; partial payments keep the occurrence open with the remaining amount.
- Editing amount or date from "next occurrence" bumps `version`; past occurrences keep their version and amount.
- Month-end edge cases: due day 31 falls back to the last day of shorter months.

### 6.7 UI

- **Money page tabs:** Overview · Transactions · Budgets · Bills & income · Goals.
- **Overview (one screen, max 4 visuals):** 4 number tiles (income received, spent, left in budget, saved this month); a category utilisation bar list sorted by risk; an upcoming bills list (next 14 days); a 6-month income vs expense chart. Trends and savings detail sit one click deeper.
- **Today integration:** one Money row (spent today, left this month, next bill).
- **Alerts:** in-app and Telegram at 80% and 100% of a category, 3 days before a bill, on the day of expected income.

### 6.8 AI agent integration

| Tool | Access kind | Confirmation |
| --- | --- | --- |
| `finance_summary`, `finance_query` (spend by period, category, merchant; compare months) | read | None |
| `finance_affordability` (purchase amount → impact on budget and end balance) | read | None |
| `finance_draft_transaction`, `finance_draft_budget` | prepare (draft only, not saved) | Shown as a card |
| `finance_record_transaction`, `finance_update_budget`, `finance_change_recurring` | **financial** (new access kind) | Always one-tap approval; never auto-approved by any autonomy preset |
| `finance_delete_transaction` | destructive | Always approval + 30-day soft delete |

The agent answers only from tool results. When data is missing it says so ("No expenses recorded for 12–18 Nov") rather than estimating. Every agent-created row stores `created_by=agent` and its `approval_id`.

## 7. AI agent gap analysis

The agent has 59 tools and a strong approval model, but it cannot answer most of your daily questions because the read tools for goals, trends, habits and money do not exist. Its tool routing also drops tools unpredictably.

**Current tools by access kind (from `GET /api/agent/capabilities`):** 23 read, 19 prepare, 14 execute, 3 destructive. Execute and destructive always pause for approval (`application/security/permissions.py` `approval_required`).

### Verified defects

1. **Blind tool routing.** When no skill matches and more than 12 tools are eligible, `select_tools` asks the fast model to pick groups. The prompt contains only the group names, never the user's message (`application/model_router.py` lines 67–79; `application/tools/selection.py` deletes `history`). The choice is effectively random, and `life` tools such as `learn_save_items` vanish. **Fix:** pass the latest user message to the router, or drop the router and use deterministic skill/intent matching; make the selection once per run, not once per round.
2. **Skills over-narrow tools.** A matched skill restricts tools to its groups (e.g. plan-my-time → google only). A planning question that also needs tasks or goals loses them. **Fix:** treat skill groups as a priority, not a filter; always include `tasks`, `life` and `goals` reads.
3. **Prepare tools change external state without approval.** `google_gmail_mark_read` and `google_gmail_label` are `prepare`, so they alter real Gmail without asking. That conflicts with the README promise that anything leaving your hands waits for approval. **Fix:** reclassify as execute, or add a per-tool "Allow" default the owner opts into.
4. **Raw tool output reaches the UI.** Steps without a structured `summary` display their raw output in chat cards.

### Can the agent answer your questions today?

| Question | Today | Missing piece |
| --- | --- | --- |
| What should I focus on today? | Yes (calendar + tasks) | Habits, overdue weighting |
| What tasks are overdue? | Yes (`task_list`) | — |
| What did I fail to complete yesterday? | Partly (`day_summary`) | Outcome notes summary |
| How productive was I this week? | No | `days_stats` / analytics read tool |
| Priorities tomorrow? | Partly | Tomorrow's day view tool |
| Am I falling behind on goals? | No | There is no `goal_list` or goal-progress read tool (only `goal_create`, `plan_propose`) |
| Any finance question (spend, budget, afford, compare months, upcoming bills) | No | Entire finance tool set (Section 6.8) |

### Missing tools to add

- **Reads:** `goal_list`, `goal_progress`, `days_stats`, `habit_status`, `week_review`, `inbox_list`, `routine_list`, the finance reads, and a cross-module `life_snapshot` (today's events, tasks, habits, money and goals in one call).
- **Prepare (drafts):** `habit_checkin_draft`, `reschedule_plan` (proposes moving overdue tasks across the week with reasons), `finance_draft_*`.
- **New access kind `financial`:** always requires approval, never auto-allowed, separate daily cap, shown with amount and account in the approval card.

### Proactive opportunities (use the existing scheduler and proactive gate)

| Trigger | Action | Channel |
| --- | --- | --- |
| Category reaches 80% / 100% of budget | Alert with remaining amount and days left | In-app + Telegram |
| Bill due in 3 days | Reminder with "Mark paid" | Needs you |
| Expense > 2× the category's 30-day average | "Unusual spend" note | In-app |
| Habit missed 3 days running | Ask why; offer a smaller target | Evening wrap-up |
| 5+ overdue tasks | Propose a reschedule plan (approval) | Morning briefing |
| Sunday evening / 1st of month | Weekly and monthly review reports | Docs or in-app |

The proactive gate (`proactive_gate.py`) already enforces quiet hours and a daily cap. The "Proactive" autonomy preset is labelled "not active yet"; turn it on only for read and draft actions.

## 8. Security and architecture report

No critical vulnerability was found. The main risks are reliability (scheduler, cold starts) and data integrity (missing constraints, two date models), plus session handling that should improve before financial data is added.

### Security findings

| # | Finding | Evidence | Risk | Fix |
| --- | --- | --- | --- | --- |
| S1 | Sessions cannot be revoked; logout and password change do not invalidate existing tokens | Stateless HMAC token, 12 h (`routers/_common.py` `valid_dashboard_session`); logout only deletes the cookie | Medium (High once finance exists) | Server-side session table with id, created, last\_seen; revoke on logout and password change; 30-day sliding "remember me" for daily use |
| S2 | One secret signs sessions and derives the token-encryption key | `DASHBOARD_SECRET_KEY` used for both (`google/tokens.py`) | Medium | Separate `TOKEN_ENCRYPTION_KEY`; document rotation |
| S3 | Gmail-modifying tools run without approval | `google_gmail_mark_read`, `google_gmail_label` are `prepare` | Low–Medium | Reclassify (Section 7) |
| S4 | Internal tick/reset secret compared with `!=` | `demo_routes.py` line 214 | Low | `secrets.compare_digest` |
| S5 | Public demo reset endpoint | `/api/demo/reset` is public (rate-limited) | Low | Require the internal secret or limit to nightly job |
| S6 | Life endpoints accept untyped JSON bodies | `routers/life.py` uses `JsonBody`; validation lives in services | Low | Pydantic models with `extra="forbid"` for schema, docs and rejection of unknown fields |
| S7 | Health details hidden from anonymous users | `/api/health` returns only `{status}` without a session | Good | — |

Verified good: PBKDF2-SHA256 310k rounds; login lockout (429 after 5 failures); origin check blocks cross-site writes (403); CSP `default-src 'self'`, `frame-ancestors 'none'`, HSTS in production; Google tokens AES-256-GCM; wipe and forget-all need a token plus a typed phrase; no secrets found in the repository.

### Data integrity findings

| # | Finding | Evidence | Fix |
| --- | --- | --- | --- |
| D1 | Two task date concepts disagree | Today list uses `due_at` (`domain/task_rules.py` TODAY view); Plan and score use `plan_date` | Define one rule: a task is "on" a day if `plan_date` = day, or `due_at` falls on it while `plan_date` is null; one shared query |
| D2 | No foreign keys from `owner_user_id` to an owner table; owner hard-coded as `"dashboard"` | `models.py`, `_common.py` `DASHBOARD_OWNER` | Owner table + FKs; keeps the door open for a second user (family member) |
| D3 | Status, priority and outcome stored as free strings | `TaskRow.status String(32)` | DB `CHECK` constraints matching the enums |
| D4 | Two name fields | `workspace_accounts.name` vs `owner_profile.name` | Single source (profile); account name becomes login label only, or sync on save |
| D5 | Routine schedules split between notification prefs and automations | `notification_service.py` maps `wrapup_time` to `daily_wrapup` only, while `evening_wrapup` exists separately | Merge the two wrap-ups; one settings source |
| D6 | Unknown request fields silently dropped | `recurrence` accepted with 201 | `extra="forbid"` on all request models |

### Architecture and operations

| # | Finding | Impact | Fix |
| --- | --- | --- | --- |
| A1 | Scheduler driven by GitHub Actions cron every 5 min (`.github/workflows/tick.yml`) | GitHub delays or drops scheduled runs at busy times; 5 AM reminders can be late | A real always-on worker (paid Render instance, Fly.io machine, or Supabase `pg_cron` calling the tick) |
| A2 | API on Render **free** plan (`render.yaml`) sleeps when idle | 30–60 s cold starts; skeletons for 5–10 s+; ticks wake it each time | Paid instance (\~$7/month) or keep-warm; required for a daily-use app |
| A3 | Today calls Google Calendar live on every load; activity paged 3 × 200 rows | Slow first paint | Cache agenda for 5 min; a `/api/activity/count?since=` endpoint |
| A4 | Fast-model router call on every agent round | Extra latency and nondeterminism | Select tools once per run |
| A5 | 13 MB unrelated HTML file at repo root (`Workforce_Intelligence_Task_Copy_Helper_Updated.html`) | Repo bloat, confusion | Remove from main |
| A6 | No OpenAPI schema exposed in local mode; life routes untyped | Harder for frontend and tests | Typed routers; generate the TS client from OpenAPI |

Test coverage is strong for the backend (798 tests incl. security and approval flows) but thin for cross-screen consistency: no test asserts that Today, Plan and day stats agree. Add contract tests for the day snapshot and Playwright journeys for the four daily scenarios.

## 9. Prioritized improvement roadmap

Five P0 items (about 2 weeks) restore trust in the numbers and timing; finance should start only after the recurrence engine (P1-1) lands. Complexity: S = 1–3 days, M = 1–2 weeks, L = 3–6 weeks.

| ID | Priority | Problem | Proposed solution | User impact | Complexity | Depends on |
| --- | --- | --- | --- | --- | --- | --- |
| P0-1 | P0 | Today hides tasks planned for today and all overdue work (D1) | One day-membership rule + shared `DaySnapshot` query used by Today, Plan, stats and agent | Morning view becomes correct | M | — |
| P0-2 | P0 | Agent drops tools at random (blind router) | Pass the user message to the router or replace it with deterministic matching; select once per run | Learn saving and other tools work reliably | S | — |
| P0-3 | P0 | Late or missed reminders and briefings; 30–60 s cold starts | Always-on API instance + real scheduler (worker or `pg_cron`) | Routines fire on time; app opens fast | S (config) + cost | — |
| P0-4 | P0 | Wrong name, conflicting wrap-up times, contradicting counts | Single name source; merge wrap-up routines; trust report and "things this week" from the same query | Numbers can be trusted | S | P0-1 |
| P0-5 | P0 | Sessions can't be revoked | Server-side sessions, revoke on logout and password change; sliding 30-day session | Safe for financial data | M | — |
| P1-1 | P1 | No recurrence anywhere | `recurrence_rules` + occurrence generator shared by tasks, habits, bills, income | Routines stop being manual | M | P0-3 |
| P1-2 | P1 | No habits | Habits with check-ins, streaks, Today habit row | Morning routine in two taps | M | P1-1 |
| P1-3 | P1 | No finance | Finance module per Section 6 (ledger, recurring, budgets, savings, dashboard) | Core requested capability | L | P1-1, P0-5 |
| P1-4 | P1 | Agent cannot read goals, stats or money | Read tools + `financial` access kind (Section 7) | Answers daily and money questions from real data | M | P1-3 for finance tools |
| P1-5 | P1 | Raw JSON in chat; Needs you opens empty; duplicate suggestions | Human summaries per tool; first non-empty tab; dedupe by source | Cleaner daily use | S | — |
| P1-6 | P1 | Calendar hides earlier events today | Use start of day in owner timezone for "Today" | Full schedule visible | S | — |
| P1-7 | P1 | Mobile not designed | Bottom bar + quick-add sheet; responsive tables | Capture on the go | M | P1-2, P1-3 |
| P2-1 | P2 | No projects, subtasks, dependencies | Project entity, `parent_id`, `blocked_by` | Real work planning | M | P0-1 |
| P2-2 | P2 | No time tracking | Timer + manual entries per task/project | "Where did my day go" | M | P2-1 |
| P2-3 | P2 | No learning paths | Course and certification goal templates with milestones and hours | Learning progress visible | M | P2-2 |
| P2-4 | P2 | No weekly/monthly reviews | Analytics service + review routines and pages | Continuous improvement | M | P1-2, P1-3 |
| P2-5 | P2 | Data integrity gaps | Owner FKs, CHECK constraints, `extra="forbid"`, typed life routes | Fewer silent errors | M | — |
| P2-6 | P2 | Gmail tools change state without approval | Reclassify as execute or opt-in Allow | Consistent safety promise | S | — |
| P3-1 | P3 | Developer jargon in UI | Technical details behind a disclosure | Calmer UI | S | — |
| P3-2 | P3 | Default 404, US dates, routine name casing, sidebar scrollbar | Polish pass | Professional feel | S | — |
| P3-3 | P3 | Repo hygiene | Remove 13 MB HTML; separate token key; `compare_digest` | Maintainability | S | — |
| P3-4 | P3 | Reading limited to Bible templates | Books and article plans | Broader reading goals | S | — |

**Suggested sequence:** weeks 1–2 all P0 → weeks 3–4 recurrence + habits → weeks 5–9 finance + finance agent tools → weeks 10–11 mobile and UX P1 items → then P2 by value.

## 10. Recommended future product architecture

Keep the current modular monolith; it is the right shape for one owner. Add two shared services, a recurrence engine and a day snapshot, so every module and the agent see the same day, the same schedule and the same numbers.

&#91;embedded content: target architecture · channels, API and agent, life modules, shared services, data\]

The web app and Telegram call the API; chat goes from the API to the agent, which reaches modules only through its tool registry. The scheduler triggers routines through the agent as well. Habits, Finance and recurring tasks all generate their occurrences from the one recurrence engine. Today, the weekly review and the agent all read the one snapshot, which removes the contradictions found in Section 3.

**How modules talk:**

1. **Synchronous:** API and agent tools call application services; services own validation and write through repositories.
2. **Events:** services emit domain events (`task.completed`, `expense.recorded`, `habit.checked`, `budget.threshold_crossed`) to the existing run-events/job queue. Analytics, notifications and proactive suggestions subscribe to these events, not to each other.
3. **Cross-module links by id only:** a transaction can reference a project or a goal, a habit can count toward the day score, a savings goal extends a Goal. No module reads another module's tables directly.
4. **One permission gate:** every write, from the UI or the agent, passes the same policy. Financial writes from the agent always create an approval.

## 11. Test method and limitations

Every result marked Pass or Fail was executed; anything only read in code is labelled as code evidence.

- **Code audited:** `mikias1219/AI-Agent` at commit `b225457` (backend about 28,000 lines of Python, Next.js frontend, 22 migrations).
- **Isolated environment:** local FastAPI + fresh SQLite database, offline "fake" model provider, test owner account. No production data was read or changed by these tests.
- **Live site:** navigation and screenshots only, plus two chat prompts and one Learn "Ask Compass" click on your account. Nothing was accepted, dismissed, deleted or changed in settings.
- **Not tested:** real-model agent quality locally (no API key); Gmail, Calendar writes, Drive backup and Telegram (need test Google and Telegram credentials); mobile layout (the browser window could not be resized); Playwright suite and live evals; Postgres-specific behaviour (tests ran on SQLite); load and performance beyond observed timings.
- **Assumptions:** monetary figures in Section 6 are the sample values you gave; complexity estimates assume one experienced full-stack developer.
