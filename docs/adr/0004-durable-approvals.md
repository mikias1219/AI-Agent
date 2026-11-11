# ADR 0004: Approvals are persisted; runs pause and resume

- Status: Accepted
- Date: 2026-11-11

## Context

P3 (APR-01..06, BR-02..05). Approvals waited on an in-process thread event for 120 seconds
(`DashboardApprovalNotifier`). A restart, a sleeping free-tier host or a slow owner lost the
request, and the chat request held a thread the whole time.

## Decision

- `approvals` rows are the source of truth: arguments, `arguments_hash` (SHA-256 of canonical
  JSON), risk, plain summary, `untrusted_content`, `expires_at` (24 h, `APPROVAL_TTL_SECONDS`),
  `decided_by`, `channel`, `result`, link to run and tool call. Statuses: `pending`, `approved`,
  `denied`, `expired`, `executed`, `failed`, plus `superseded` for edited approvals.
  Migration `20261111_06` (SQLite and PostgreSQL; pre-existing pending rows are expired because
  they have no hash).
- `ApprovalGatewayImpl` has three modes. With an interactive notifier (CLI) it asks inline. In
  durable mode (default when no notifier is wired: dashboard, Telegram) it persists the request,
  emits `approval.required` and raises `ApprovalPendingError`. Without either, it defers.
  `DashboardApprovalNotifier` is removed.
- The agent loop parks the pending call, marks the rest of the round "Not run", and stops with
  `stop_reason=awaiting_approval`. `ChatService` saves the run as `awaiting_approval` (not
  terminal, thread released). A durable `approval.required` ends the event stream; a restarted
  process replays it from storage.
- `POST /api/approvals/{id}/decision` goes through `ApprovalService`. Approve is a
  compare-and-set `pending -> approved`, then `ToolRegistry.execute` with `ctx.approval_id`.
  The gate's `claim` checks tool name, arguments hash, expiry and flips `approved -> executed`
  in one `UPDATE ... WHERE status = 'approved'`, so concurrent or repeated approves run the
  tool once (BR-03); repeats return the recorded outcome. The run then resumes on a worker
  thread (`ChatService.resume_run`) and AURA reports the result. Deny and expiry finish the run
  with a deterministic message, no model call.
- Edit-then-approve never mutates an approval: the old row becomes `superseded`, a new pending
  row with the new hash is created, and `approval.edited` is audited with both hashes (APR-06).
  Edited arguments are re-validated against the tool schema.
- Expiry is enforced at decide time, by the gate, and by a sweep (on list, at startup and every
  minute in the dashboard process). The owner is told on the paused run.
- Only the channels `dashboard` and `telegram_private` may decide (APR-04). Group chats and
  unknown channels get `ApprovalForbiddenError`; Telegram inline buttons are not built yet.
- Tools whose output is external content (Gmail, Calendar, Drive reads) set
  `ToolSpec.untrusted_output`; the registry flags the run context and later approvals carry
  `untrusted_content` (BR-04), shown as a warning on the card.
- UI: one `ApprovalCard` in Chat (inline, continues the same answer after a decision) and in
  Tasks → Approvals and the notifications drawer.

## Consequences

- A paused run survives restarts; approving after the restart executes once and completes the run.
- A run that dies mid-execution after `executed` but before `finished` keeps `executed` with no
  result; it is never executed again.
- If the owner chats again while a run waits, the stored transcript has an unanswered tool call.
  `arrange_tool_results` adds a "not run yet" placeholder for the model and, once decided, moves the
  real result next to its call.
- Telegram inline approve buttons, "approve all steps" (APR-08) and the Today/Inbox placements are
  later phases. Telegram-originated runs pause and are decided on the dashboard.
