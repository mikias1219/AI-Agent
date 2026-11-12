# AURA Phase 1 / P8 — Telegram hardening

**Date:** 2026-11-12  
**Status:** In progress  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P8** (INT-TG-01..03; BR-12)

## Goal

Owner private chat replies to every real message except acknowledgements/emoji (no English keyword gate). Groups reply only on mention and never get private-owner tools. Approvals can be decided via Telegram inline Approve/Deny only from the owner private chat. Reminders and briefings deliver here.

## Scope

- Rewrite `needs_reply` / reply gate: language-independent silence set (acks + emoji-only); otherwise reply in private allowlisted chats
- Group chats: require bot mention (entities or `@username`); `identity_user_id` stays None so tools cannot see owner private data
- Parse `callback_query` updates; Approve/Deny for approval ids; reject non-owner / group / spoofed / duplicate callbacks
- Send approval prompts with inline keyboard when a run pauses for approval from Telegram origin
- Confirm reminder/briefing delivery uses Telegram when channel includes telegram
- Tests: Arabic/French/Spanish samples reply; emoji silent; group without mention silent; spoofed + duplicate callbacks

## Out of scope

- INT-TG-04 voice notes
- MCP / web (P9)

## Decisions

1. **Silence set:** Unicode-aware emoji-only and a small multilingual ack lexicon (ok/merci/شكرا/gracias/…) plus pure reactions; not English request-hint lists.
2. **Owner private chat:** `chat_id == sender_id` and `chat_id > 0` and in allowlist.
3. **Callback data:** `apr:{approval_id}:{approve|deny}` with constant-time allowlist check on callback `from.id` and `chat.id` must be the owner private chat.
4. **Idempotency:** ApprovalService already executes once; duplicate callbacks answer with already-decided status.
