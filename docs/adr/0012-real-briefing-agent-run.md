# ADR 0012 — Real briefing as an AgentRun

## Status

Accepted (Phase 4 / R1)

## Context

The daily briefing previously wrote a fixed “Calendar: nothing scheduled.” line and
recorded a synthetic `AgentRun` with model `scheduler`. That violated transparency
(BR-10) and AUT-02 when Google was connected.

## Decision

- Gather briefing sources through `ToolRegistry.execute` (calendar and Gmail when
  connected; tasks and approvals from services).
- Compose the narrative with the normal `Agent` loop and `prompts/briefing_v1.md`.
- Persist a real run (model label, prompt version, tool steps) and store structured
  sections JSON on the automation `last_result` for the UI.

Unavailable sources say so; one failed source does not fail the whole briefing.

## Consequences

- Tests assert no hard-coded calendar claim remains in source.
- Later UI clarity (V2) can render sections without parsing raw prose.
