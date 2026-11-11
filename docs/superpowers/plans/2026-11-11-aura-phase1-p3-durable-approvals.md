# P3 Durable Approvals Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice.

**Goal:** Durable pause/resume approvals with single-use execution and shared ApprovalCard.

**Architecture:** Persist approval; end stream with approval.required; decision API executes once and resumes run worker; FE ApprovalCard.

## Global Constraints

- Spec + proposal P3; BR-03 single-use; BR-05 email send always needs approval
- Keep ToolRegistry gate; offline tests
- Do not build P4–P8 here

### Task 1: Persist approvals + pause

- [ ] Extend approval model/store; DashboardApprovalNotifier → durable
- [ ] Run status awaiting_approval; tests for persist across “restart” (new process / new notifier)

### Task 2: Decision + resume + idempotency

- [ ] POST decision; execute once; resume run; expire job/check
- [ ] Edit args → new approval; untrusted warning flag

### Task 3: ApprovalCard UI

- [ ] Shared card in Chat (and Approvals tab); plain summary + Approve/Deny/Edit

### Task 4: Verify + mark spec Implemented
