# ADR 0006 — Durable scheduler and protected tick

## Status

Accepted

## Context

Free-tier API sleep and process restarts must not drop reminders or daily briefings. A cron-only in-memory loop is not enough; GitHub Actions can wake the API every few minutes if the endpoint is protected.

## Decision

- Persist jobs, reminders, and automations in SQL (SQLite/Postgres) behind JobQueue / ReminderStore / AutomationStore ports.
- Process due work from an in-process lifespan worker and from `POST /internal/tick` authenticated with constant-time compare of header `X-Aura-Tick-Secret` (`INTERNAL_TICK_SECRET`, falling back to the dashboard secret in local/dev).
- Use idempotency keys (`reminder:{id}:deliver`, `briefing:{owner}:{date}`) so duplicate ticks deliver once.
- Label reminders late when delivery is more than five minutes after `remind_at` (BR-07). Briefings are AgentRuns with origin `automation` under the same approval gates (BR-14). Empty calendars yield “nothing scheduled”; never invent events.

## Consequences

- `.github/workflows/tick.yml` can keep production warm and process due work without a paid always-on worker.
- Automations UI and Inbox reminders stay honest: every row comes from the store, not mocks.
