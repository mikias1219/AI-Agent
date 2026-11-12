# P8 Telegram Hardening Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice. Isolated worktree.

**Goal:** Language-independent reply gate, group mention privacy, inline Approve/Deny, Telegram delivery for reminders/briefings.

**Architecture:** Rewrite telegram_reply_gate; extend mapper/runner for mentions and callbacks; client inline keyboards; ApprovalService decision from callback path.

**Tech Stack:** Existing TelegramBotClient long-poll, ApprovalService, ChatService, pytest offline mocks.

## Global Constraints

- Spec + proposal P8; BR-12; offline tests; no English keyword request lists
- Do not build P9–P11 here

### Task 1: Reply gate + group mention

- [x] Replace needs_reply with ack/emoji silence; private always else
- [x] Groups require mention; disable private identity
- [x] Tests: AR/FR/ES reply; emoji silent; group no-mention silent

### Task 2: Inline approvals + callbacks

- [x] send_message with reply_markup; parse callback_query
- [x] Runner decides approve/deny only from owner private chat; duplicate-safe
- [x] Tests: spoofed callback ignored; duplicate callback once

### Task 3: Delivery + docs

- [x] Verify reminder/briefing Telegram send path
- [x] ADR + mark Implemented
