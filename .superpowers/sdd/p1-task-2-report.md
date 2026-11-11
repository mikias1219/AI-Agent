# P1 Task 2 report — Date resolution + TaskService

Commit: `feat(tasks): service search, views, and date resolution`

## Delivered
- `domain/dates.py`: `resolve_relative_date(text, timezone, now=)` (today/tonight/tomorrow, weekday, next weekday, 3pm/3:30pm/15:00/noon/midnight, in N min/hours/days/weeks/months, end of month, ISO date), `add_months` (month-end clamp). Unknown text -> None; bad tz -> ValueError. Calendar math on wall-clock; "in N hours" absolute; DST-gap times normalised.
- `domain/task_rules.py`: `new_task` takes P1 fields; `transition` sets `completed_at` entering DONE and clears on leaving; `reopen`; `TaskView` (today/upcoming/overdue, non-overlapping, by owner-local day) + `matches_view`.
- `TaskService`: create (new fields), update (UNSET sentinel; `due_at=None` clears), search (all words vs title/notes/project/tags), list(view/owner/include_deleted/now/timezone; deleted excluded by default), get(include_deleted), advance, reopen, soft_delete (idempotent). Audit events task.updated / task.deleted.
- Persistence fix: SQLite dropped tzinfo, storing wall-clock; repository now stores due/completed/deleted in UTC and reads back aware UTC.
- `tools/builtins/tasks.py`: tiny None-guard so mypy passes now that `get` is typed.

## Tests
- `tests/unit/test_dates.py` (19: DST spring/fall, gap, in-24h, month-end, leap, year rollover, tz day boundary)
- `tests/unit/test_task_service_p1.py` (views, search, soft delete, reopen, completed_at)

## Verification (backend)
pytest 197 passed; ruff check/format clean; mypy domain+application clean; import-linter 2 kept.

## Notes
- Repository port unchanged; filtering is in the service (in-memory) — fine at current scale.
- Bare weekday = today-or-later; `next <weekday>` strictly later. Date-only defaults to 09:00.
- No README/ADR change: no new decision beyond spec; frontend untouched. `progress.md` left uncommitted for controller.
