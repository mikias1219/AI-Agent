# P11 Demo + Portfolio Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice.

**Goal:** `/demo` isolated workspace + portfolio README/docs for v1.0.

**Architecture:** `get_demo_app()` + seed + SIMULATED tool wrap; Next.js `/demo` shell; docs polish.

### Task 1: Demo backend

- [x] Demo settings, container, seed, SIMULATED wrap, rate limit, reset endpoint
- [x] `/api/demo/*` routes; nightly reset workflow; tests

### Task 2: Demo UI + Activity filters

- [x] `/demo` layout with banner; wire demo API client
- [x] Activity channel/status filters (UX-13)

### Task 3: Portfolio docs

- [x] README top fold; CONTRIBUTING; issue templates; v1.0 notes
- [x] Remove `.superpowers/`; ADR; mark Implemented
