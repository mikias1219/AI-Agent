# AURA Phase 1 / P7 — Google workflows

**Date:** 2026-11-12  
**Status:** In progress  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P7** (INT-GOO-01..05; BR-04)

## Goal

Gmail and Calendar tools cover search/read/draft/reply and free-slot/delete under the ToolRegistry gate. Scopes split into read vs write; Connections exposes a Read-only switch. Every external payload is size-limited, sanitized, labeled untrusted, and never followed as instructions. Create-task-from-email is a first-class action.

## Scope

- Split OAuth into `GOOGLE_READ_SCOPES` and `GOOGLE_WRITE_SCOPES`; request write only when Read-only is off
- Persist `google_read_only` (owner setting / token metadata) and block prepare/execute/destructive Google tools when on
- Connections Google UI: plain-language granted scopes + Read-only toggle
- Tools (names may keep `google_` prefix for registry consistency):
  - `gmail_search` / `gmail_read` (read; sanitize + size cap; untrusted)
  - `gmail_create_draft` (prepare)
  - `gmail_reply` (execute; approval)
  - `calendar_find_free_slots` (read)
  - `calendar_delete_event` (destructive)
- Keep existing list/send/create/update where still useful; wire them through the same read-only gate
- Wrap outputs with an untrusted envelope; registry already sets `ctx.untrusted_content` via `untrusted_output`
- `create_task_from_email` (prepare or execute per task create policy) linking Gmail message id → task
- Tests: mocked Google HTTP, scope/read-only handling, injection sample does not send, size limits

## Out of scope

- INT-GOO-04 Drive write; Drive stays read-only list/search as already shipped
- Full Today agenda fill beyond using calendar tools when connected (P5 empty state remains until calendar list feeds UI if already present)
- Telegram hardening (P8), MCP (P9)

## Decisions

1. **Read-only default:** Prefer safer default after reconnect — Read-only on until the owner turns it off and re-consents write scopes.
2. **Sanitize:** Strip HTML to text, truncate body (e.g. 8 KiB), prefix tool output with `UNTRUSTED_EXTERNAL_CONTENT:` and never execute tool calls derived solely from that text in tests.
3. **Draft vs send:** `gmail_create_draft` is prepare (no approval); `gmail_reply` / send remain execute.
4. **Delete:** `calendar_delete_event` is destructive (approval + high risk).
5. **Task from email:** Creates a task with title from subject and note/metadata holding message id; does not auto-send.
