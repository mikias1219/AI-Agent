# P5 Today Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice. Isolated worktree.

**Goal:** Today home, Inbox, first-run wizard, Help/How-to, checklist, chat cards.

**Architecture:** Replace Overview with Today; profile onboarding fields; FE screens reuse ApprovalCard and live APIs only.

## Global Constraints

- Proposal P5; no mock data; hide Automations; agenda empty until real calendar
- Fix any open P4 CI failures in the same stream before merge if still red

### Task 0: Unblock CI from P4 if still red

- [ ] Fix backend/frontend/e2e failures on `8dc0bc2`

### Task 1: Onboarding + checklist API

- [ ] Profile/onboarding fields + migration if needed
- [ ] Mark checklist items from real events (chat, task, approval, memory)

### Task 2: Today + Inbox + nav

- [ ] Nav restructure; Today page; Inbox page

### Task 3: Wizard, Help, chat cards

- [ ] First-run wizard; Help panel; How to use; chat cards

### Task 4: Playwright checklist flow + mark Implemented
