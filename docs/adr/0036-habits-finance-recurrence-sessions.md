# ADR 0036 — Recurrence, habits, finance, time, projects, sessions

## Status

Accepted

## Context

The product assessment (`AURA — Product Assessment & Roadmap.md`) found that Today, Plan and the day
score disagreed about which tasks belong to a day, that nothing could repeat (prayer, rent,
weekly reports), that personal finance did not exist, that the tool router dropped tools at
random, and that sessions could not be revoked.

## Decision

Consistency (P0)
- One day-membership rule in `domain/task_rules.effective_day`: a task is on `plan_date`, else on
  the local date of `due_at`. Today, Overdue and Upcoming all use it; Today also lists overdue.
- Tool selection passes the user's message to the router, always offers `core`, `tasks`, `life`,
  `goals` and `finance`, and chooses once per run.
- Server-side sessions (`user_sessions`): logout and password change revoke; "keep me signed in"
  is a sliding 30 days; the signed cookie alone is no longer enough.
- The old `evening_wrapup` routine folds into `daily_wrapup`; the profile is the single source of
  the display name; `TOKEN_ENCRYPTION_KEY` can separate token encryption from session signing.

Recurrence and habits (P1)
- `domain/recurrence.py` is the one engine (daily, weekly, monthly, quarterly, yearly, interval,
  weekdays, month-end clamp). Habits, recurring tasks and finance rules use it.
- Finishing a recurring task creates the next one (idempotent by `source_ref`).

Finance (P1)
- Amounts are integers in minor units. `fin_transactions` hold real money only; `fin_occurrences`
  hold expected items and become transactions when settled. Editing a rule creates a new version
  from the next occurrence; history is never rewritten. Transfers are two linked rows.
- New access kind `financial` (`domain.models.APPROVAL_KINDS`): always asks, ignored by any
  per-tool Allow and by every autonomy preset. Agent-created rows store `created_by=agent` and the
  `approval_id`.
- Gmail mark-read and label tools are now `execute` (they change a real mailbox).

Structure and time (P2)
- Projects (progress from tasks carrying the name), one level of subtasks, `blocked_by` links with
  loop detection, time entries (one running timer), learning paths as goals with milestones and
  target hours, weekly and monthly review from one service shared by API and agent tool.
- Request bodies of tasks and all new routers reject unknown fields (422).

## Consequences

- Undated tasks default to today, so they appear on Today (tests updated).
- Existing browser sessions must sign in once after deploy.
- Production should run an always-on instance (`render.yaml` plan `starter`); the in-process
  scheduler ticks every 30 s.
- Not done: owner foreign keys and CHECK constraints on legacy tables (new tables have them).
