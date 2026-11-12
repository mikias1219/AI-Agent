# ADR 0014 — Integration tool selection and ModelRouter

## Status

Accepted (Phase 4 / R3)

## Context

`select_tools` used English regexes, so non-English requests kept or dropped the wrong
tools. There was no fast/smart role split for routing vs chat.

## Decision

- Group tools by integration (`core`, `tasks`, `reminders`, `memory`, `google`, `web`,
  `telegram`, `mcp`) and keep only connected groups plus core.
- When more than 12 tools remain, ask the fast model for a JSON group list.
- Add `ModelRouter` with fast/smart labels (`MODEL_FAST` / `MODEL_SMART`) and provider
  fallback; expose active models on `GET /api/status` and Settings → Runtime.

## Consequences

- Selection no longer depends on English keywords.
- HermesAgent still uses its own path; plain `Agent` receives connected + router.
