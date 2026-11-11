# AURA Phase 1 / P4 — Memory

**Date:** 2026-11-11  
**Status:** Implemented  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P4** (MEM-01..06, 08; BR-08)

## Goal

Replace read-only newest-first facts with owner-controlled memories: propose-then-confirm writes, hybrid retrieval (recency + keyword + vector), redaction, CRUD UI, and forget-all.

## Scope

- `memories` table (kind, content, source_run_id, last_used_at, embedding, soft-delete) replacing `memory_facts`
- `EmbeddingProvider` port; local hashing embedder for SQLite; pgvector path when Postgres
- Hybrid rank top 8 behind `MemoryStore`
- Tools: `memory_save` (propose / confirm via API), `memory_search`, `memory_forget`
- Redaction filter (credentials, government IDs, card numbers)
- `/api/memories` CRUD, search, forget-all with confirmation token
- UI: Memory screen, Save chip, Used memory chip, Settings → Data → Forget everything
- Capability `memory: api`; nav entry when live
- Tests: redaction, ranking, duplicates, permanent deletion, retrieval limit; W5 path

## Out of scope

- MEM-07 episodic summaries
- Today shell / Inbox redesign (P5)
- Scheduler (P6)

## Decisions

1. **Propose then confirm.** `memory_save` does not persist; it returns a proposal payload. Chat shows a Save chip; `POST /api/memories` (or confirm endpoint) persists. Explicit owner “Remember …” still goes through the same confirm path so BR-08 holds.
2. **Soft delete + hard forget-all.** Row delete sets `deleted_at`; forget-all permanently removes all rows for the user after typed confirmation token.
3. **Local-first embeddings.** Deterministic local `EmbeddingProvider` (hashing / bag-of-words) for SQLite and tests; optional hosted model later behind the same port. Postgres uses pgvector when available, else cosine over stored vectors.
4. **Kinds.** `preference` | `fact` | `person` | `routine` only.
5. **Dedup.** Same `(user_id, kind, content)` while not deleted is ignored on insert.
