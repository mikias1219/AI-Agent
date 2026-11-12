# P10 Evals + Observability Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice. Isolated worktree.

**Goal:** 25 offline eval scenarios in CI, tracing with trace ids, richer health, Activity CSV + run detail.

**Architecture:** JSON scenario harness → Agent + FakeProvider; Tracer on chat/agent; health probes; Activity export API + drawer.

**Tech Stack:** pytest, existing FakeProvider/Agent, FastAPI, Next.js Activity page.

## Global Constraints

- Spec + proposal P10; offline CI; no P11 demo rewrite here

### Task 1: Eval harness + 25 scenarios + CI/badge

- [x] harness.py + scenarios/*.json (25)
- [x] test_scenarios.py parametrize
- [x] eval CI job + badge script + live workflow stub

### Task 2: Tracing + health

- [x] Tracer + trace_id on runs; console exporter via settings
- [x] Extend /api/health

### Task 3: Activity CSV + run detail + docs

- [x] GET /api/activity/export.csv; drawer shows run steps
- [x] ADR + README badge + mark Implemented
