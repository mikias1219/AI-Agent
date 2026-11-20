# ADR-0029: Phase 5 Trust and data (export/wipe, per-tool permissions, Balanced undo)

Status: Accepted

## Context

Phase 5 of `docs/TRANSFORMAT.md` covers G6 (per-tool permissions), G5 step two (Balanced
with undo), G9 (export/wipe), and several security items.

## Decision

1. **Export** — `GET /api/export` returns a JSON snapshot (profile, tasks, memories, goals, plans,
   suggestions, recent activity). The Settings → Data UI downloads it as a file.
2. **Wipe** — `POST /api/workspace/wipe/token` then `POST /api/workspace/wipe` with phrase
   `WIPE WORKSPACE`. Clears memories (via forget-all), soft-deletes tasks, dismisses open
   suggestions, marks goals done, and clears Google tokens. Login account remains.
3. **Per-tool permissions (APR-07)** — stored on `agent_control.tool_permissions` as
   allow/ask/block. `OwnerPermissionPolicy` is consulted by the registry on every tool call.
   Hard ceilings: send/reply tools and all `destructive` tools can never be Allow (clamped to Ask).
4. **Balanced undo (AG-TRU-04)** — when autonomy preset is `balanced` and the owner has not
   explicitly set Ask/Block for `google_calendar_create`, that execute tool auto-runs. Successful
   auto-runs of reversible tools (`task_create`, `reminder_create`, `google_calendar_create`,
   `google_gmail_create_draft`) record an `undo_actions` row for 10 minutes. `POST /api/undo/{id}`
   reverses via soft-delete / cancel / Google delete (not through the agent approval path).
   Hard ceilings and Proactive remain unchanged; Proactive is still preference-only.

## Consequences

- Owners can tighten individual tools without waiting for Balanced.
- Export does not include Google OAuth secrets or dashboard password hashes.
- UI copy marks Balanced as in effect; toast and chat cards expose Undo while the window is open.
- S6 closed in ADR-0032; S8–S12 closed in ADR-0030.
