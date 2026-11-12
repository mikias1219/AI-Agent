# ADR 0018 — Today aggregate (`GET /api/today`)

## Status

Accepted (full mockup, Task 2–3)

## Context

Today previously fan-out to briefing, approvals, tasks, and status. The mockup needs one
composition with honest empty/unavailable states and no invented calendar facts.

## Decision

- Application-layer `TodayService.build(owner_id)` assembles greeting, needs_you (≤3),
  now_next (agenda + active run), plan tasks, goals, onboarding, connection warnings, and
  structured briefing sections.
- Agenda and Google warnings never invent events; disconnected → Connect CTA.
- Frontend Today v2 loads primarily from `GET /api/today`.

## Consequences

- Goals/suggestions populate as their services land; empty arrays omit UI sections.
- Stop on active run uses existing `POST /api/runs/{id}/cancel`.
