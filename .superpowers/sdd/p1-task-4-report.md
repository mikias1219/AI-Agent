# P1 Task 4 report: Tasks UI

- Tasks tab now has views Today / Upcoming / Overdue / All (default) / Done, wired to `GET /api/tasks?view=` / `?status=done` (`viewParams`, `taskListPath`).
- Quick add: title + optional due (`datetime-local` -> `due_at`) + priority (P1/P2/P3). Existing "New task" / "Add task" labels kept.
- List rows show priority badge, due badge (Today/Tomorrow/Overdue), status badge, status select; row opens a detail drawer (edit title, notes, priority, status, due/clear; PATCH).
- Per-view empty states, loading and error (with retry) retained.
- New: `features/tasks/task-views.ts` (+ vitest, 12 new tests), `task-detail-drawer.tsx`; updated `lib/api/{tasks,types}.ts`, `tasks-page.tsx`, `e2e/smoke.spec.ts` (views + drawer steps).
- Verified: `tsc --noEmit`, `format:check`, `vitest` (14 pass). Not run: Playwright e2e (no `python` binary in sandbox) and `next build`.
- Note: default view is All (Today would hide undated new tasks and break the smoke test). Due-day labels use browser-local days; backend views use the owner timezone.
