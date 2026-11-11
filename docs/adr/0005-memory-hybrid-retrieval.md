# ADR 0005 — Memory hybrid retrieval

## Status

Accepted

## Context

P4 needs owner-controlled memories with ranking by recency, keyword, and vector similarity (top 8). CI and local SQLite cannot depend on a hosted embedding API or Postgres-only extensions.

## Decision

- Introduce `EmbeddingProvider` and a deterministic local hashing embedder for default/SQLite/tests.
- Store embedding vectors on each memory row; rank with a weighted mix of recency, keyword overlap (FTS5 on SQLite when available, else substring), and cosine similarity.
- When the DB is Postgres and pgvector is available, use it for nearest-neighbor; otherwise fall back to in-process cosine over stored vectors.
- Writes go through redaction and owner confirm (Save chip / API), never silently from the model.

## Consequences

- Retrieval quality is good enough for personal prefs without ops cost in v1.
- Hosted embedders can replace the local provider later without changing MemoryStore callers.
