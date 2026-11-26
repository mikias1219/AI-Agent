# ADR 0035 — Days and achievements, Drive backup, Calendar as a view

## Status

Accepted

## Context

The owner wants Compass to be where the day is planned and measured ("I did 30 push-ups"), and
wants a tidy copy of notes, diary, files and summaries in their own Google Drive and the timed
tasks on their Google Calendar (contract: `docs/LIFE_API_CONTRACT.md`, sections 7-10). Both
syncs write to the owner's Google account, so they are commit actions (BR-02..BR-05, BR-09,
BR-14) and must never delete, share or read outside Compass's own data.

## Decision

Tasks as achievements and days
- Migration `20261127_01` adds `plan_date` (backfilled from `due_at`, else the created date,
  in the owner's timezone), `target_value`, `target_unit`, `actual_value`, `outcome`,
  `outcome_note`, `calendar_event_id`, `calendar_synced_at` to `tasks`.
- Rules are pure (`domain/task_rules.py`, `domain/days.py`). `complete`: achieved/partial ->
  done; missed/skipped -> cancelled (reopenable). Reopening clears outcome, actual value and
  completion time. A plain status change to done or cancelled records `achieved` or `skipped`,
  and legacy closed rows are counted the same way, so every closed task has an outcome.
- Score = (achieved + 0.5 partial) / (planned - skipped). `planned` counts every task of the
  day, so an open task lowers the day's score until it is finished or moved. The streak bar
  (score >= 0.8) is compared in integers, so 0.8 is never a floating point accident.
- "Today" and every task's day come from the owner's timezone once (`local_date`); after that
  days are plain dates, so DST changes cannot move a task. The `week` stat is the ISO week to
  date (Monday), the `month` stat the calendar month to date.
- A task is "timed" when its local due time is not 00:00 or 09:00 (date-only phrases resolve
  to 09:00). This is a heuristic: a task explicitly due at exactly 09:00 counts as date-only
  and needs `all_day` to reach Calendar.

Drive layout and scope
- One `Compass` folder in the owner's Drive: `Notes/{YYYY}/{YYYY-MM}/{title-slug}-{id8}.md`,
  `Diary/.../{date}.md`, `Daily/.../{date}-summary.md`, `Learning/vocabulary.md`,
  `Reading/reading-log.md`, `Files/{YYYY}/{YYYY-MM}/{original name}`. Markdown carries YAML
  front matter (`id`, `kind`, `tags`, `created`, `updated`) whose values are JSON-encoded, so a
  hostile title cannot escape it. Slugs and file names drop `/`, `\`, `..` and control
  characters; the Drive client refuses unsafe names and ids again (defence in depth) and caps
  uploads at 5 MB.
- Scope is `https://www.googleapis.com/auth/drive.file`, the narrowest Drive write scope: Compass
  can only touch files it created. It joins the write scope set, so owners reconnect Google
  once; the status endpoints report `scope_granted: false` until they do and the run endpoints
  answer 409 "Reconnect Google ...". Existing read access (`drive.readonly`) is unchanged and
  Drive content is never read back by this feature.
- Compass is the source of truth. One `drive_links` row per object keeps the Drive file id, URL
  and content hash; unchanged content is skipped, changed content overwrites the same Drive
  file. Deleting locally only marks the link (`local_deleted_at`); Compass never deletes anything
  in Drive, and wipe (BR-13) clears links and settings but never touches Drive. Folder ids are
  cached in `drive_folders`; a 404 (owner removed a file or folder) rebuilds the folders and
  creates a fresh copy.

Batch approval consent model
- A run builds a pending snapshot (at most 50 objects whose hash changed, newest first) and asks
  the tool registry to run `drive_sync_push` with exactly that list, titles included. The
  registry gate is the only path: pause, policy block, the daily commit budget and the approval
  all apply as for any other execute tool.
- Mode `ask` (default): one durable approval per run, showing counts and titles. Approving it
  is the owner's consent for those objects and no others; the approval executes once. Mode
  `auto` exists only when the owner set the tool to Allow in Settings -> Permissions (APR-07);
  the Balanced preset does not make these tools automatic. Never-allow ceilings are unchanged.
- The content is rendered when the approval is executed, so an edit between request and
  approval is written as the newer text of the same approved object; nothing outside the list
  is ever written. Note, diary and file text is data: it is rendered and uploaded, never
  interpreted, so a note saying "email my files" can neither send mail nor widen the batch
  (covered by a test and an eval scenario).
- Calendar uses the same shape: tool `task_calendar_sync` (execute, at most 25 tasks, `titles`
  shown on the approval, same ask/auto rule).

Calendar as a view
- Calendar events cannot hold a done state, so Compass stays the source of truth and Calendar is
  a view. Events are created for timed tasks (date-only with `all_day`), and on the next sync
  after a change the summary gets `✓ `, `◐ `, `✗ ` or `– ` and the description gets the outcome,
  `actual/target unit` and the note; reopening removes the prefix. A task is re-synced when it
  changed after `calendar_synced_at`. Events are never deleted; an event the owner removed in
  Calendar is recreated. Google Tasks sync is out of scope.

Automation
- Routine `daily_wrapup` (catalogue, default off, 21:00) scores the day, creates one suggestion
  ("Today: 4 of 5 done (80%). Carry 1 unfinished task over to tomorrow?") whose accept action
  is the prepare tool `day_carry_over`, and, only when Drive or Calendar sync is enabled,
  requests those batches through the registry. Quiet hours, pause and the daily cap skip the
  whole routine (BR-14). `NotificationPrefs.daily_wrapup` and `wrapup_time` are enforced
  because this routine reads them.

Agent
- Tools: `task_complete` (prepare; ambiguity returns candidates and changes nothing),
  `day_summary` (read), `day_carry_over` (prepare), extended `task_create`, `drive_sync_push`
  (execute), `drive_sync_status` (read), `task_calendar_sync` (execute). System prompt
  `system_v3` tells the agent to use `task_complete` when the owner says they did something,
  to claim completion only after a successful result and to use `day_summary` for "how did my
  day go".

## Consequences

- Owners must reconnect Google once for `drive.file`; until then Drive backup answers 409.
- A first Drive run on a large workspace takes several approvals (50 objects each); the status
  endpoint shows what is still pending.
- The 09:00 heuristic for "timed" tasks can be replaced by an explicit flag later without a
  contract change.
