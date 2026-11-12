# AURA Phase 1 / P11 — Demo mode and portfolio polish

**Date:** 2026-11-12  
**Status:** Implemented  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P11** (UX-12, UX-13)

## Goal

Ship a public `/demo` workspace that never mixes with real owner data, finish Activity filters (UX-13), and polish the repository for a v1.0 portfolio release.

## Scope

- Separate demo AppContainer on `DEMO_DATABASE_URL` (default `sqlite:///./data/demo.db`) with FakeProvider
- Seeded owner, tasks, memories, sample run/activity; execute/destructive tools return `SIMULATED: …` and never call Google/Telegram
- Rate limit on demo API; `/internal/demo/reset` + nightly workflow; permanent UI banner on `/demo`
- Activity filters by channel (origin) and status; CSV/run detail already from P10
- README top fold rewrite (pitch, GIF placeholder, live demo link, Mermaid diagram, status, badges)
- CONTRIBUTING, issue templates, `docs/releases/v1.0.md`; remove `.superpowers/` from the repo root

## Out of scope

- Full UX-06..11 (command palette, PWA, themes) unless already present
- Live cloud demo hosting config beyond documented link placeholder

## Decisions

1. **Isolation:** demo uses its own SQLite file and `get_demo_app()`; real `get_app()` never reads it.
2. **API surface:** mount authenticated-looking demo routes under `/api/demo/*` (subset: health, chat/runs, tasks, activity, approvals, memories) with a fixed demo session cookie.
3. **SIMULATED:** registry wrapper on the demo container replaces execute/destructive handlers.
