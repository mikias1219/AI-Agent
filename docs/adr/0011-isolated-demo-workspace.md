# ADR 0011 — Isolated demo workspace

## Status

Accepted

## Context

P11 (UX-12) needs a public `/demo` that visitors can try without owner credentials. Seeded and simulated data must never appear in the real owner database (FND-03).

## Decision

- Run a second `AppContainer` via `get_demo_app()` on `DEMO_DATABASE_URL` (default `sqlite:///./data/demo.db`) with `FakeProvider`.
- Expose a public `/api/demo/*` surface (session, chat, tasks, activity, reset) with per-IP rate limits.
- Wrap execute/destructive tools so handlers return `SIMULATED: …` and never call Google/Telegram.
- Reset via `/internal/demo/reset` (secret) and a nightly GitHub Actions workflow.

## Consequences

- Demo and owner schemas can migrate independently on different files.
- Portfolio visitors use `/demo` without login; the permanent banner states the simulation.
