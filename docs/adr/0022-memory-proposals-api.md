# ADR 0022 — Durable memory proposals

## Status

Accepted (mockup UI v2 parity)

## Context

MEM-02 requires Save-chip confirmation before writes. The Memory **Proposed**
tab in the mockup lists pending proposals with Save / Dismiss. Propose used to
validate only and never persist, so the tab could only show an empty state.

## Decision

- Persist pending rows in `memory_proposals` (migration `20261113_01`).
- `memory_save` creates a proposal with an id; chat Save chip and Memory →
  Proposed confirm via `POST /api/memories/proposals/{id}/confirm` or dismiss
  via `…/dismiss`. Confirmed proposals become normal memories; nothing is
  written until confirm.
- `GET /api/memories/proposals` lists open proposals for the owner.

## Consequences

- Proposed tab is truthful against the API.
- Appearance theme remains local-only (ADR 0021); memory proposals are durable.
