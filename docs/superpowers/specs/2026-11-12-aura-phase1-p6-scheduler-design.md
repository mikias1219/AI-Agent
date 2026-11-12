# AURA Phase 1 / P6 — Scheduler, reminders, daily briefing

**Date:** 2026-11-12  
**Status:** In progress  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P6** (AUT-01..05, TSK-05; BR-07, BR-14)

## Goal

Jobs survive restart and free-tier sleep: a durable queue, an in-process worker, and a protected `/internal/tick` called every 5 minutes from GitHub Actions. Reminders deliver once (late-labeled if >5 min). Daily briefing is an AgentRun with origin `automation` under the same gates. Automations screen to enable/edit/run.

## Scope

- Tables: `jobs`, `reminders`, `automations` (+ Alembic)
- `JobQueue` port + SQLAlchemy adapter (SQLite/Postgres)
- Worker loop in API lifespan; `POST /internal/tick` with constant-time secret header
- `.github/workflows/tick.yml` every 5 minutes
- Reminder create (API + tool), delivery to Telegram + Inbox list, late label (BR-07), idempotent retries
- Daily briefing automation: agenda stub (empty → “nothing scheduled”), due/overdue tasks, pending approvals; AgentRun origin automation; deliver to Today + Telegram
- Automations nav + screen: enable/disable, schedule time, Run now, last result
- Tests: duplicate tick once, restart delivery, late label, empty calendar copy

## Out of scope

- AUT-03 templates (weekly review, meeting prep) beyond daily briefing
- AUT-06 playbooks
- Full Google calendar fill (P7); briefing never invents events

## Decisions

1. **Tick secret:** `INTERNAL_TICK_SECRET` (falls back to `DASHBOARD_SECRET_KEY` in local/dev). Header `X-Aura-Tick-Secret`.
2. **Idempotency:** job keys like `reminder:{id}:deliver` and `briefing:{owner}:{YYYY-MM-DD}`.
3. **Late:** delivered_at − remind_at > 5 minutes → status/detail includes `late`.
4. **Briefing run:** builds a read-only summary through application services (no COMMIT tools); records AgentRun with origin `automation`.
5. **Inbox Reminders tab** lists reminder rows (pending/sent), not mock data.
