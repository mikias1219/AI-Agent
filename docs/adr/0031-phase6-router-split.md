# ADR-0031: Phase 6 — routers, import-linter, frontend data, a11y

Status: Accepted

## Context

Phase 6 of `docs/TRANSFORMATION.md` covers splitting `presentation/web/app.py`, extending
import-linter, hardening the frontend data layer, and a light accessibility pass.

## Decision

1. **Routers.** Domain groups live under `presentation/web/routers/` as
   `build_*_router(container, …)` factories: agent, workspace, auth, tasks, goals,
   runs/chat, Google, integrations, memory, today/inbox. `create_dashboard_app` mounts
   them; middleware, CORS, and health stay in `app.py`.
2. **import-linter.** Application must not import infrastructure, presentation, or `app`.
   Demo seed and Google/Telegram builtins avoid typing against those layers.
3. **Frontend data.** `lib/client-cache/cache.ts` dedupes and briefly caches GETs;
   `api()` invalidates on mutations; `usePolling` pauses while the tab is hidden and
   refreshes on focus (shell badges). Named `client-cache` so it is not caught by the
   repo-root `data/` gitignore.
4. **a11y.** Skip link to `#main-content`; Tabs keep tabpanel nodes with `hidden`;
   Needs you uses panels. Drawer/Modal already trap focus from Phase 1.

## Consequences

- New HTTP endpoints go in routers, not the app factory monolith.
- S6 token encryption is recorded separately in ADR-0032.
