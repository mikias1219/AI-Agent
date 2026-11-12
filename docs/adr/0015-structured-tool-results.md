# ADR 0015 — Structured tool results and chat cards

## Status

Accepted (Phase 4 / R4)

## Context

Chat cards guessed kinds by matching words in tool names/output. `ToolResult` was a
plain string, so the UI could not render typed receipts reliably.

## Decision

- Extend `ToolResult` with `result_type`, `id`, `summary`, and `fields`.
- Persist `result_type` / `result_json` on run steps (migration `20261112_06`).
- Emit structured fields on `tool.finished`; frontend `cardsFromSteps` renders by
  `result_type`, with unknown types falling back to a generic receipt.
- Remove unused `frontend/lib/mocks/notifications.ts`.

## Consequences

- Built-in tools declare `result_type` on `ToolSpec`; JSON outputs enrich id/summary.
- Keyword matching in chat cards is gone.
