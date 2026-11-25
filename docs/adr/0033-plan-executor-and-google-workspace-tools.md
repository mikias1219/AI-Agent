# ADR 0033 — Plan executor and Google Workspace tools

## Status

Accepted

## Context

Approving a plan recorded authorization but ran steps without arguments, kept no results, and
never handled commit steps. The agent also could not search Drive, read Docs/Sheets, or change
mailbox, document or calendar-invite state (BR-02..BR-05, INT-GOO-*).

## Decision

Plan executor
- `PlanStep` gains `arguments`, `result` and `approval_id` (migration `20261125_01`).
- Steps run strictly in order through `ToolRegistry.execute`; the first step that is not done
  stops the walk. read/prepare steps run on plan approval. A commit step goes through the
  registry's normal gate: a durable approval is created, its id stored on the step, and the
  plan pauses (`needs_ok`). `ApprovalService` notifies a listener after an approval executes
  or is denied; the executor then continues. `POST /api/plans/{id}/resume` does the same on demand.
- Execute once: a step is saved as `running` before the call; a `running` step found later
  is marked failed and never re-run. An approval is claimed once by the registry (BR-03).
  Finished steps are skipped on every resume. Denied, expired or failed approvals fail the step.
- Registry gates are unchanged (pause, policy, schema, commit budget BR-09). Output of
  `untrusted_output` tools is stored with an `[UNTRUSTED_EXTERNAL_CONTENT]` prefix, and the
  approval of a later step carries `untrusted_content` (BR-04).

Google tools (all through the same registry; every write is also blocked by the client when Read-only is on)
- read: `google_drive_search`, `google_drive_read` (Docs/Slides exported as text, 20k chars, 2 MB cap),
  `google_sheets_read` (200 rows x 26 columns). All untrusted.
- execute: `google_docs_create`, `google_docs_append`, `google_sheets_append_rows` (values stored RAW,
  so formulas are never evaluated), `google_gmail_archive`, `google_calendar_respond`.
- prepare: `google_gmail_mark_read`, `google_gmail_label` (reversible; TRASH/SPAM/SENT/DRAFT refused).
- No tool sends email without the existing approved `google_gmail_send`/`reply` path (BR-05).
- Scopes: read adds `spreadsheets.readonly`; write adds `documents` and `spreadsheets`
  (Drive reads reuse `drive.readonly`; Gmail/Calendar reuse `gmail.modify` and `calendar.events`).

## Consequences

- Existing connections must re-consent to use Docs/Sheets writes and Sheets reads.
- Superseded (edited) approvals leave a plan paused until the owner resumes it; not auto-followed.
- Plan steps must carry their own arguments; the model supplies them when proposing.
