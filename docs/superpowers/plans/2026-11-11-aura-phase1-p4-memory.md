# P4 Memory Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice. REQUIRED: isolated worktree.

**Goal:** Owner-controlled memories with hybrid recall, tools, API, Memory UI, Save/Used chips, forget-all.

**Architecture:** Expand MemoryStore + EmbeddingProvider; migrate facts → memories; redaction on write; tools propose/search/forget; REST CRUD; FE Memory + chat chips.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite FTS5 (+ pgvector when Postgres), Next.js App Router, Vitest/pytest.

## Global Constraints

- Spec + proposal P4; BR-08 no silent writes; no credentials/IDs/cards stored
- Offline unit tests; no hosted embedding required for CI
- Do not build P5–P8 here

### Task 1: Schema + domain + redaction

- [ ] Migration `memories` (+ FTS); migrate/drop `memory_facts`
- [ ] Domain Memory + redaction filter with unit samples
- [ ] EmbeddingProvider + local embedder

### Task 2: MemoryStore hybrid recall + service

- [ ] Store: create/list/update/delete/search/forget_all; mark last_used; top 8 hybrid
- [ ] MemoryService wrapping store + redaction
- [ ] Tests: ranking, duplicates, permanent deletion, limit

### Task 3: Tools + API

- [ ] `memory_save` / `memory_search` / `memory_forget` tools
- [ ] `/api/memories` CRUD, search, forget-all + confirmation token
- [ ] Wire container + chat recall to hybrid top 8; expose used memory ids in run/chat payload

### Task 4: UI

- [ ] capability `memory`; nav Memory; Memory screen
- [ ] Save chip + Used memory chip in chat
- [ ] Settings → Data → Forget everything

### Task 5: Verify + mark spec Implemented
