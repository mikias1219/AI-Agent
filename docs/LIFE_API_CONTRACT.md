# Compass Life modules: API contract

Status: agreed contract for the "personal life" expansion. Backend and frontend are built in
parallel against this file. If a shape must change, change it here first and tell the lead.

Conventions

- All routes are under `/api`, owner-scoped through the existing session (single owner, `DASHBOARD_OWNER`).
- JSON in, JSON out. Times are ISO 8601 UTC strings. Dates are `YYYY-MM-DD` in the owner's timezone.
- Errors: FastAPI default `{"detail": "..."}`. 400 invalid input, 404 missing, 413 too large, 415 type not allowed.
- Lists return a bare JSON array, newest first, and accept `limit` (default 50, max 200) and `offset`.
- IDs are opaque strings (32 hex chars).
- Nothing here is mock data. Empty is empty.
- Export (BR-13) and workspace wipe must include every new table.
- Agent tools are `prepare` or `read` class only (records the owner can see and delete). No tool deletes.

## 1. Notes and diary (`notes` table, one table, two kinds)

```
Note = {
  id, kind: "note" | "diary", title: string (<=200), body: string (markdown, <=50000),
  tags: string[] (<=10, each <=30, lowercase), mood: "great"|"good"|"okay"|"low"|"bad"|null (diary only),
  entry_date: "YYYY-MM-DD" | null (diary only; one diary entry per date), pinned: boolean,
  created_at, updated_at
}
```

- `GET /api/notes?kind=note|diary&q=&tag=&limit=&offset=`: `q` searches title and body (case-insensitive substring). Pinned first for kind=note, then newest. Diary sorted by `entry_date` desc.
- `POST /api/notes`: body `{kind, title?, body, tags?, mood?, entry_date?, pinned?}` -> 201 Note. Diary without `entry_date` uses today in the owner's timezone. A second diary entry for the same date -> 409 `{"detail":"A diary entry for this date already exists."}`.
- `GET /api/notes/{id}`, `PATCH /api/notes/{id}` (any subset), `DELETE /api/notes/{id}` -> 204.
- `GET /api/notes/stats` -> `{"notes": int, "diary_entries": int, "diary_streak_days": int, "wrote_diary_today": boolean}`. Streak = consecutive days ending today (or yesterday if today is not written yet).

Agent tools: `note_create` (prepare; args `title?`, `body`, `tags?`), `note_search` (read; `query`, `limit<=10`), `diary_add` (prepare; `body`, `mood?`, `entry_date?`, appends to the day's entry if one exists instead of failing).

## 2. Files and images (`files` table, content stored in the database)

```
FileItem = {
  id, name: string, mime: string, size: int (bytes), kind: "file" | "image",
  description: string (<=500), tags: string[], created_at,
  url: "/api/files/{id}/content"
}
```

- `POST /api/files`: JSON `{name, mime, data_base64, description?, tags?}` -> 201 FileItem. Max 5 MB decoded -> 413. Allowed mimes: `image/png`, `image/jpeg`, `image/webp`, `image/gif`, `application/pdf`, `text/plain`, `text/markdown`, `text/csv`, `application/json`; anything else (including `image/svg+xml`) -> 415. Verify magic bytes for images/pdf match the declared mime, else 415. `kind` is `image` for `image/*`.
- `GET /api/files?kind=file|image&q=&tag=&limit=&offset=`: `q` searches name and description.
- `GET /api/files/{id}/content`: raw bytes, `Content-Type` = stored mime, `X-Content-Type-Options: nosniff`, `Content-Disposition: inline` for images and pdf, `attachment; filename=...` for the rest. Auth required (cookie).
- `PATCH /api/files/{id}` `{name?, description?, tags?}`, `DELETE /api/files/{id}` -> 204.
- `GET /api/files/stats` -> `{"files": int, "images": int, "bytes": int}`.
- Total storage cap for the owner: 200 MB -> 413 `{"detail":"Storage limit reached."}`.

Agent tool: `file_search` (read; `query`, `kind?`, `limit<=10`) returns metadata and, for text files up to 20 000 chars, the text wrapped as untrusted external content (BR-04).

## 3. Learning (`learn_items` table)

```
LearnItem = {
  id, kind: "word" | "phrase" | "fact", term: string (<=200), meaning: string (<=1000),
  example: string (<=1000), language: string (BCP-47-ish, default "en"), topic: string (<=60) | "",
  box: int (0..5, Leitner), next_review_at: string, times_correct: int, times_wrong: int,
  created_at, updated_at
}
```

- `GET /api/learn/items?q=&topic=&language=&due=true&limit=&offset=`; `due=true` only items with `next_review_at <= now`.
- `POST /api/learn/items` single or `{"items":[...]}` batch (max 20) -> 201 `LearnItem[]`. Duplicate `term` (case-insensitive, same language) is skipped, not an error; response lists only created items.
- `PATCH /api/learn/items/{id}`, `DELETE /api/learn/items/{id}` -> 204.
- `POST /api/learn/items/{id}/review` body `{"result":"know"|"again"}` -> LearnItem. Leitner intervals by box: 0:10 minutes, 1:1 day, 2:3 days, 3:7 days, 4:14 days, 5:30 days. know -> box+1 (max 5), again -> box 0.
- `GET /api/learn/stats` -> `{"total": int, "due": int, "learned": int (box>=3), "streak_days": int, "reviewed_today": int}`.
- `GET /api/learn/topics` -> `string[]`.

Agent tools: `learn_save_items` (prepare; `items[]` of `{term, meaning, example, kind?, language?, topic?}` max 20), `learn_due` (read; `limit<=10`). The prompt guidance for "teach me N words": answer in chat with term, meaning, one example each, then call `learn_save_items` so they appear in the Learn page.

## 4. Reading (Bible or any reading plan; references only, no bundled scripture text)

```
ReadingPlan = {
  id, name: string (<=120), items: string[] (ordered references, e.g. "John 3:1-21", max 1500),
  position: int (index of the next item), active: boolean, created_at, updated_at,
  next: string | null (items[position] or null when finished), progress: float 0..1
}
ReadingLog = { id, reference: string (<=120), read_on: "YYYY-MM-DD", reflection: string (<=5000), plan_id: string | null, created_at }
```

- `GET /api/reading/plans`, `POST /api/reading/plans` `{name, items?, template?}` where `template` is one of `"gospel-of-john-21"`, `"psalms-30"`, `"proverbs-31"`, `"new-testament-90"` (server expands to ordered chapter references; `items` wins if both given) -> 201 ReadingPlan. `GET /api/reading/templates` -> `[{id, name, description, count}]`.
- `PATCH /api/reading/plans/{id}` `{name?, active?, position?}`, `DELETE /api/reading/plans/{id}` -> 204.
- `POST /api/reading/plans/{id}/advance` body `{reflection?}` -> `{"plan": ReadingPlan, "log": ReadingLog}`: logs `plan.next` as read today and moves `position` by one. 409 if the plan is finished.
- `GET /api/reading/logs?plan_id=&limit=&offset=`, `POST /api/reading/logs` `{reference, read_on?, reflection?, plan_id?}` -> 201, `PATCH`/`DELETE /api/reading/logs/{id}`.
- `GET /api/reading/stats` -> `{"logs": int, "streak_days": int, "read_today": boolean, "active_plan": ReadingPlan | null}`.

Agent tools: `reading_next` (read; returns the active plan's next reference), `reading_log` (prepare; `reference`, `reflection?`, advances the active plan if the reference matches `next`).

## 5. Profile, photo, password, notifications

Extends `GET/PATCH /api/profile`. Profile payload gains:

```
Profile = {
  name, email, timezone, language,
  bio: string (<=500), birthday: "YYYY-MM-DD" | null,
  has_photo: boolean, photo_url: "/api/profile/photo" | null,
  member_since: string
}
```

- `PATCH /api/profile` accepts `name, timezone, language, bio, birthday`. Invalid timezone -> 400.
- `PUT /api/profile/photo` JSON `{mime, data_base64}`: png/jpeg/webp only, max 1 MB, magic bytes verified -> `{"photo_url": "/api/profile/photo"}`. `GET /api/profile/photo` raw bytes (nosniff, auth required, `Cache-Control: private, max-age=0, must-revalidate` plus ETag). `DELETE /api/profile/photo` -> 204. Photo is stored apart from the Library files list.
- `POST /api/auth/password` `{current_password, new_password}` -> 204. Verifies current (401 `{"detail":"Current password is incorrect."}`), new password 12..128 chars and not equal to current (400), rotates the session so other sessions are signed out, writes an audit entry without the password, rate-limited like login.
- `GET /api/profile/notifications` / `PATCH /api/profile/notifications`:

```
NotificationPrefs = {
  channels: { in_app: boolean, telegram: boolean },
  daily_briefing: boolean, reminders: boolean,
  learning_daily: boolean, reading_daily: boolean, diary_nudge: boolean,
  learning_time: "HH:MM", reading_time: "HH:MM", diary_time: "HH:MM",
  quiet_hours: { enabled: boolean, start: "HH:MM", end: "HH:MM" }
}
```

Each flag must be honoured by a real producer, or the backend reports it as not enforced in the response field `enforced: string[]` (the keys that do something today). The UI shows a control only for keys listed in `enforced`.

## 6. Today additions

`GET /api/today` gains an optional `life` object (absent means the owner has not used these yet):

```
life = {
  learn: { due: int, total: int, next_term: string | null },
  reading: { next: string | null, plan_name: string | null, read_today: boolean, streak_days: int },
  diary: { wrote_today: boolean, streak_days: int },
  notes: { recent: [{id, title, updated_at}] }   // up to 3
}
```

---

# Part 2: days, achievements, Drive and Calendar sync

Same conventions as above. These sections extend tasks and add the Drive and Calendar sync.
Backend and frontend build in parallel against this file.

## 7. Tasks as achievements, and days

Task gains these fields (existing fields unchanged):

```
plan_date: "YYYY-MM-DD"            // the day this task belongs to, owner timezone. Defaults to the date of due_at, else today.
target_value: number | null        // e.g. 30
target_unit: string                // e.g. "push-ups", "" when none (<=20 chars)
actual_value: number | null        // what the owner really did
outcome: "achieved" | "partial" | "missed" | "skipped" | null
outcome_note: string               // <=500
calendar_event_id: string | null   // set once synced to Google Calendar
calendar_synced_at: string | null
```

- `POST /api/tasks` and `PATCH /api/tasks/{id}` accept `plan_date`, `target_value`, `target_unit`, `actual_value`, `outcome`, `outcome_note`.
- `GET /api/tasks?plan_date=YYYY-MM-DD` and `GET /api/tasks?from=YYYY-MM-DD&to=YYYY-MM-DD` filter by plan date (existing filters keep working).
- `POST /api/tasks/{id}/complete` body `{outcome?, actual_value?, note?}` -> Task.
  - `achieved` or `partial` -> status `done`, `completed_at` set.
  - `missed` or `skipped` -> status `cancelled` (reopenable to `planned`), `completed_at` null, outcome kept.
  - `outcome` omitted: with a target and `actual_value`: `actual >= target` -> achieved, `0 < actual < target` -> partial, `actual == 0` -> missed; with no target, or no actual: achieved.
  - Validation: `actual_value` >= 0; `outcome` must agree with a given `actual_value` only loosely (the owner may override); 404 if missing.
  - Reopening (status back to `planned`) clears `outcome`, `actual_value` and `completed_at`.
- `POST /api/days/{date}/carry-over` body `{to?: "YYYY-MM-DD"}` (default next day) -> `{"moved": int, "to": "YYYY-MM-DD", "task_ids": string[]}`. Moves tasks of that date whose status is `planned`, `in_progress` or `blocked` by changing `plan_date`. Never touches done or cancelled tasks.
- `GET /api/days/{date}` ->

```
Day = {
  date, is_today: boolean,
  tasks: Task[],                                  // plan_date == date, ordered by due time then created
  summary: { planned: int, done: int, achieved: int, partial: int, missed: int, skipped: int, open: int, score: number | null },
  events: { id, title, startsAt, location }[],    // Google Calendar events that day (read), [] when not connected
  calendar_connected: boolean,
  diary: Note | null,
  readings: ReadingLog[],
  learned: { reviewed: int }                      // flashcard reviews that day
}
```

  `planned` counts every task of the day. `open` = planned, in_progress, blocked. `score` = (achieved + 0.5 * partial) / (planned - skipped), or null when that denominator is 0.
- `GET /api/days/range?from=&to=` (max 62 days) -> `{date, planned, achieved, partial, missed, skipped, open, score}[]` one row per day that has at least one task.
- `GET /api/days/stats` -> `{ "streak_days": int, "week": {planned, achieved, partial, missed, rate}, "month": {same} }`. A day counts toward the streak when it has at least one task, no open tasks, and score >= 0.8. Streak = consecutive counting days ending today (or yesterday if today still has open tasks). `rate` = score over the period (null when nothing planned).

Agent tools (through the registry): `task_create` gains `target_value`, `target_unit`, `plan_date`. New `task_complete` (prepare): `{task_id?, title_query?, outcome?, actual_value?, note?}`; if `task_id` is missing it matches `title_query` against open tasks of today (case-insensitive substring); exactly one match is completed, zero or several returns the candidates and does nothing. New `day_summary` (read): `{date?}` returns the Day summary and task lines. The agent must say a task is finished only after a successful `task_complete` result.

## 8. Google Drive: organized storage

Compass writes under one folder in the owner's Drive using the narrowest scope, `https://www.googleapis.com/auth/drive.file` (files created by Compass only). It is added to the write scope set; owners reconnect Google once. Nothing outside Compass's own folder is read or changed by this feature.

Layout (Markdown with YAML front matter `id`, `kind`, `tags`, `created`, `updated`; filenames are slugged, never contain `/`, `..` or control characters):

```
Compass/
  Notes/{YYYY}/{YYYY-MM}/{title-slug}-{id8}.md
  Diary/{YYYY}/{YYYY-MM}/{YYYY-MM-DD}.md
  Daily/{YYYY}/{YYYY-MM}/{YYYY-MM-DD}-summary.md   // that day's tasks, outcomes, score, reading, words reviewed
  Learning/vocabulary.md                            // all words as a table, regenerated
  Reading/reading-log.md                            // all readings, regenerated
  Files/{YYYY}/{YYYY-MM}/{original file name}
```

Rules: Compass is the source of truth; an update overwrites the Drive copy (same Drive file id, tracked per object). Deleting locally never deletes in Drive (the link is marked and left). Folder ids are cached. A `drive_links` record per object stores `object_type`, `object_id`, `drive_file_id`, `drive_url`, `content_hash`, `synced_at`. Unchanged content (same hash) is skipped.

`Note` and `FileItem` payloads gain `drive_url: string | null` and `drive_synced_at: string | null`.

Endpoints:
- `GET /api/drive-sync/status` -> `{ connected, scope_granted, enabled, mode: "ask" | "auto", root_url: string | null, last_sync_at, last_error, include: {notes, diary, daily, files, learning, reading}, pending: {notes: int, diary: int, daily: int, files: int, learning: boolean, reading: boolean} }`. `mode` is `auto` only when the owner set the tool policy for `drive_sync_push` to Allow in Settings -> Permissions, else `ask`.
- `PATCH /api/drive-sync/settings` `{enabled?, include?}` -> status.
- `POST /api/drive-sync/run` -> `{ "status": "awaiting_approval" | "done" | "nothing_to_do", "approval_id": string | null, "summary": {created, updated, skipped, failed} | null }`. It goes through the tool registry like any commit action: with mode `ask` it creates one approval and returns `awaiting_approval`; the approval is the owner's consent for that exact batch. 409 `{"detail":"Google Drive is not connected."}` or `{"detail":"Reconnect Google to allow Drive backup."}` when the scope is missing.
- `GET /api/drive-sync/items?object_type=&limit=&offset=` -> `{object_type, object_id, drive_file_id, drive_url, synced_at}[]`.

Tools: `drive_sync_push` (execute class, never destructive, never deletes): args `{items: [{type, id}], }`, a snapshot of at most 50 objects chosen when the approval is requested, so the approval shows exactly what will be written (counts and titles). More than 50 pending means the run takes the first 50 and reports the rest as pending. `drive_sync_status` (read).

## 9. Google Calendar sync for tasks

- Tasks that have a due time (a `due_at` with a time of day) can be pushed to Google Calendar as events: `calendar_event_id` and `calendar_synced_at` are set. Date-only tasks are not pushed unless `all_day: true` is requested.
- On completion the event is updated on the next sync: summary prefixed `✓ ` (achieved), `◐ ` (partial), `✗ ` (missed), `– ` (skipped); description gets the outcome and `actual/target unit` and the note.
- Calendar events cannot hold a done state, so Compass stays the source of truth. Google Tasks sync is not part of this release.
- `GET /api/calendar-sync/status` -> `{ connected, scope_granted, enabled, mode: "ask" | "auto", last_sync_at, last_error, pending: int }` (`auto` only when the policy for `task_calendar_sync` is Allow).
- `PATCH /api/calendar-sync/settings` `{enabled?}`; `POST /api/calendar-sync/run` same response shape as Drive (`awaiting_approval` | `done` | `nothing_to_do`).
- Tool `task_calendar_sync` (execute class): args `{task_ids: string[], all_day?: boolean}` snapshot of at most 25 tasks. Uses the existing calendar create and update client methods and the existing `calendar.events` scope.

## 10. Automation

- New routine kind `daily_wrapup` in the routine catalogue (default off, evening, default `21:00` owner time, configurable like other routines):
  1. Computes that day's summary (section 7).
  2. Creates one suggestion: "Today: 4 of 5 done (80%). Carry 1 unfinished task over to tomorrow?" Accepting performs the carry-over (a prepare action). Nothing is created when there were no tasks.
  3. If Drive sync is enabled, requests the Drive batch (Daily summary, new notes, diary); if Calendar sync is enabled, requests the calendar batch. Both go through the registry, so with mode `ask` they create approvals; with mode `auto` they run.
  4. Honours quiet hours, pause and the daily cap like every routine.
- `NotificationPrefs` gains `daily_wrapup: boolean` and `wrapup_time: "HH:MM"`, listed in `enforced` only because the routine reads them.
- `GET /api/today` gains `day: { date, summary: <Day.summary>, next_task: { id, title, due_at } | null }` (always present).
- Export (BR-13) and wipe include the new task fields, `drive_links` and sync settings. Wipe never deletes anything in the owner's Drive; the UI must say so.

## 11. Habits, finance, time, projects and review (ADR 0036)

Amounts are integers in minor units (santim for ETB) with a 3-letter currency. Request bodies reject
unknown fields (422). Money writes by the agent need approval (`financial` access kind).

Habits
- `GET/POST /api/habits`, `PATCH/DELETE /api/habits/{id}` (delete = archive).
- `GET /api/habits/today` -> `{day, items[{id,name,status:"open|done|skipped",streak}], done, due, rate}`.
- `GET /api/habits/grid?days=7`; `POST /api/habits/{id}/checkins {day?, status, value?, note?}`
  (a skip needs a note; one check-in per habit per day); `DELETE /api/habits/{id}/checkins/{day}`.
- Rule shape: `{freq: daily|weekly|monthly|quarterly|yearly, interval?, weekdays?, day_of_month?, start?, end?}`.

Tasks (additions)
- `recurrence` (rule above), `parent_id` (one level), `blocked_by[]`; responses add `subtasks {done,total}` and
  `blocked`. Finishing a recurring task creates the next occurrence.

Finance (`/api/finance`)
- `GET/POST accounts`, `categories`; `GET/POST transactions` (+ `PATCH/DELETE {id}`, soft delete),
  `POST transactions/quick {amount, category_id?}`, `POST parse {text}` (draft only, never saves).
- `GET/POST recurring`, `PATCH recurring/{id}` (new version from the next occurrence),
  `GET occurrences?from&to`, `POST occurrences/{id}/settle {status: paid|partial|skipped, amount?}`.
- `GET/POST budgets`, `PUT budgets/{id}/lines`, `POST budgets/{id}/copy {period}`.
- `GET/POST savings-goals`, `POST savings-goals/{id}/contributions`.
- `GET summary?period=2026-11`, `GET alerts`, `GET reports/monthly|category`.

Time, projects, review
- `GET /api/time/running`, `POST /api/time/start|stop`, `POST/GET /api/time/entries`, `GET /api/time/summary`.
- `GET/POST /api/projects`, `PATCH/DELETE /api/projects/{id}` (progress counted from tasks with that project name).
- Goals gain `kind` (goal|course|certification|skill|book), `target_hours`, `milestones[{id,title,done}]`,
  and `studied_hours` (from time entries linked by `goal_id`).
- `GET /api/review?period=week|month`.
- Sessions: `POST /api/login {password, email?, remember?}`; logout and password change revoke server-side.
