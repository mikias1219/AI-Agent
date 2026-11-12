# ADR 0020 — Calendar and Mail screens

## Status

Accepted (full mockup, Task 7)

## Context

Nav links for Calendar and Mail were stubs. Spec requires Google-backed screens with
Connect CTAs when disconnected and no mock events/messages.

## Decision

- Calendar week view uses `GET /api/google/status` + `GET /api/google/calendar`.
- Mail list+detail uses Gmail list endpoints; content flagged Untrusted; send/draft still
  via Chat approvals.
- Reuse `ConnectPrompt` for disconnected OAuth.

## Consequences

- No dedicated proposal overlay until suggestions/plans supply dashed events.
- Full message body read API remains tool/chat-side for now; UI shows list snippets.
