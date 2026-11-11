# Speed + Clarity Implementation Plan

> **For agentic workers:** Execute task-by-task. Checkboxes for tracking.

**Goal:** Fast Important Gmail pages, readable notifications, clear Telegram status/activity.

**Architecture:** Parallel page-scoped Gmail metadata; FE notification field rows; Telegram status simplification.

**Tech Stack:** existing httpx client, Next.js drawer/Telegram features

## Global Constraints

- Gmail remains `is:important`, ≤100 window
- Notifications: no JSON dump
- Telegram: no Start/Stop/Verify return
- Keep UI simple

### Task 1: Fast Gmail list

- [ ] Change `list_gmail` to only metadata-fetch the current page chunk; parallelize GETs
- [ ] Accumulate refs with pageToken up to needed index / 100
- [ ] Tests for query + parallel page slice
- [ ] Commit

### Task 2: Notification labeled fields

- [ ] Replace JSON pre with title + field rows in `notifications-drawer.tsx`
- [ ] Commit

### Task 3: Telegram clarity

- [ ] Simplify `telegram-status-panel.tsx` + empty/activity copy on page
- [ ] Commit

### Task 4: Verify + ship

- [ ] pytest + ruff + prettier; merge/push/deploy; remove worktree if used
