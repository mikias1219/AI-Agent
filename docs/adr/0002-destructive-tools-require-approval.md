# ADR 0002: Destructive tools require approval; tasks use soft delete

- Status: Accepted
- Date: 2026-11-11

## Context

P1 adds task deletion. `AccessKind` only distinguished `read`, `prepare` and `execute`, and only
`execute` tools were gated by human approval, so a delete tool would have run unattended.

## Decision

- Add `destructive` to `AccessKind`. `PermissionPolicy.approval_required` is true for both
  `execute` and `destructive` tools, so `ToolRegistry.execute` always asks a human first.
- `task_delete` is `destructive` and only soft-deletes (sets `deleted_at`); rows remain in storage.
- Dashboard `DELETE /api/tasks/{id}` is a direct user action in an authenticated session and
  soft-deletes without a second prompt; `GET /api/tasks?include_deleted=true` can still list them.
- Timezone for due dates comes from `owner_profile` (`GET/PATCH /api/profile`, owner `dashboard`);
  tools use the calling user's profile and fall back to UTC.

## Consequences

- Any future tool that removes or irreversibly changes data declares `destructive`.
- Hard purge of deleted tasks is out of scope and needs its own decision.
