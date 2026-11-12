# ADR 0013 — Reminder tools and real-registry evals

## Status

Accepted (Phase 4 / R2)

## Context

`reminder_create` existed only as an eval spy. Scenarios built a private registry and
could not catch registry/schema drift.

## Decision

- Register `reminder_create` (prepare), `reminder_list` (read), `reminder_cancel`
  (execute) via `SchedulerService`.
- Extend `task_update` with optional `remind_at`.
- Eval harness builds the real builtin registry with stubbed Google/web adapters;
  scenarios may not declare spy tools.
- Contract test requires schema, access_kind, result_type, and ≥1 scenario per tool.
- `evals-live.yml` reports scripted and live pass rates separately.

## Consequences

- Scenario JSON uses real tool names and seeds stable ids when needed.
- Gated scenarios keep durable approval; other scenarios auto-approve so prepare/execute
  tools can complete offline.
