# P7 Google Workflows Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice. Isolated worktree.

**Goal:** Read/write Google scope split, Read-only switch, Gmail/Calendar tools with untrusted envelopes, create-task-from-email.

**Architecture:** Extend GoogleApiClient + oauth scope sets; gate write tools on owner `google_read_only`; ToolRegistry tools with access_kind and untrusted_output; Connections UI toggle.

**Tech Stack:** Existing FastAPI/SQLAlchemy Google client, ToolRegistry, Next.js Connections Google page, httpx mocks in pytest.

## Global Constraints

- Spec + proposal P7; BR-04 untrusted labeling; offline mocked Google HTTP
- Never invent calendar events; size-limit email bodies
- Do not build P8–P11 here

### Task 1: Scopes + Read-only setting

- [ ] Split read/write scope constants; token metadata stores granted set + read_only flag
- [ ] API get/patch Google connection settings; block write client methods when read_only
- [ ] Tests: write tool rejected when read_only; reconnect requests write scopes when off

### Task 2: Gmail/Calendar client methods + tools

- [ ] Client: search, read (sanitize), create_draft, reply, find_free_slots, delete_event
- [ ] Register tools with correct access_kind + untrusted_output; create_task_from_email
- [ ] Tests: injection body does not cause send; size truncate; free slots + delete approval path

### Task 3: Connections UI + docs

- [ ] Google page: scope list + Read-only switch + error/loading/empty
- [ ] ADR + README + feature-status if needed; mark design Implemented
