# ADR 0034 — Life modules and files stored in the database

## Status

Accepted

## Context

Compass is becoming the owner's daily place for notes, a diary, files and images, language
learning and Bible or other reading plans (contract: `docs/LIFE_API_CONTRACT.md`). These are
records the owner can see and delete, so the agent may create them (prepare) and read them,
never delete. Files are the sensitive part: BR-13 requires export and wipe to be complete, and
BR-04 says content from outside is untrusted. NFR-SEC rules out shipping a new upload framework
or a new third-party dependency for a single-owner workspace.

## Decision

Files in the database
- File content is a `LargeBinary` column in `files`; metadata and content share one row and one
  transaction, so export, wipe and backup need no second store and cannot drift apart. Listing
  never loads the BLOB (`defer`).
- Upload is base64 inside JSON, so `python-multipart` is not needed. The size is checked on the
  encoded string before decoding. Caps: 5 MB per file (413), 200 MB per owner (413 "Storage
  limit reached."). If the cap is ever too small, the same API can move content to object
  storage behind `FileRepository` without a contract change.
- Allowlist: png, jpeg, webp, gif, pdf, text/plain, markdown, csv, json (anything else 415).
  SVG is refused because it can carry script. Declared type must match magic bytes for images
  and PDF; text types must not contain NUL bytes (415).
- Serving: `X-Content-Type-Options: nosniff`, `Content-Disposition: inline` only for images and
  PDF, `attachment` with a sanitized and RFC 5987 encoded name otherwise. Session cookie required.
- The profile photo lives in its own `profile_photos` table (png/jpeg/webp, 1 MB, ETag and
  `Cache-Control: private, max-age=0, must-revalidate`) so it never appears in the Library.
- `file_search` returns metadata and, for text files, up to 20 000 characters wrapped as
  `untrusted` external content. The tool is `untrusted_output`, so any later approval carries the
  untrusted warning; sending still needs approval (tested with an injection sample).

Life modules
- Tables: `notes` (kind `note` or `diary`, unique per owner, kind and entry date, so a second diary
  entry for a date is a 409), `files`, `learn_items` (casefolded `term_key`, unique per owner and
  language), `learn_reviews` (one row per review so streaks survive deleting an item),
  `reading_plans`, `reading_logs`. One Alembic migration `20261126_01` adds them and the
  `owner_profile` columns `bio`, `birthday`, `notification_prefs`, `created_at` (SQLite and Postgres).
- Domain rules are pure (`domain/life.py`): validation, Leitner boxes (10 min, 1, 3, 7, 14, 30
  days), streak maths (consecutive days ending today, or yesterday when today is not recorded yet,
  evaluated in the owner's timezone), and reading templates expanded server side to ordered
  chapter references. No scripture text is bundled.
- Application services are owner-scoped and audit ids and counts only, never content. Routers
  validate nothing themselves: domain `LifeError` subclasses map to 400, 404, 409, 413, 415 by one
  exception handler, so invalid input is always `{"detail": ...}` with 400, not FastAPI's 422.
- Agent tools (`note_create`, `diary_add`, `learn_save_items`, `reading_log` prepare;
  `note_search`, `file_search`, `learn_due`, `reading_next` read) go through the registry. None
  deletes. System prompt `system_v2` tells the agent to teach in chat first and then call
  `learn_save_items`.

Notification preferences
- Routine flags and times are stored on the routine's automation row (`daily_briefing`,
  `learning_daily`, `reading_daily`, `diary_nudge`), so the Automations page and this API cannot
  disagree. Channels, reminders and quiet hours live on the owner profile. The scheduler applies
  them in its proactive gate: Telegram needs `channels.telegram`, reminders need `reminders`,
  quiet hours fall back to the owner setting when a routine has none, and the pause and daily cap
  still apply. Nudges are built from real rows (nothing due, already read or already written
  means nothing is sent) and delivered like the briefing: in-app as a suggestion with a source,
  Telegram through the gate.
- `enforced` lists only keys that a producer reads today. All ten are wired now; a key must be
  removed from `ENFORCED_KEYS` if its producer is ever removed.

Password change and sessions
- The dashboard session key is an HMAC of the stored password hash, so changing the hash
  invalidates every other cookie; the response sets a fresh cookie for the caller. The attempt is
  rate limited with the login lockout store and audited without either password. A password that
  comes from `DASHBOARD_PASSWORD_HASH` (no account row) cannot be changed here (409).

Export and wipe (BR-13)
- Export adds notes, diary, files (with base64 content), learning items and reviews, reading
  plans and logs, the profile extras and the photo. Wipe deletes all of them and clears bio and
  birthday.

## Consequences

- Backups and exports can be large (up to 200 MB of base64). Acceptable for one owner; the
  repository seam allows object storage later.
- A text file is only as safe as the model that reads it, so the gate, not the wrapper, is the
  protection: every send, share or delete stays behind approval.
