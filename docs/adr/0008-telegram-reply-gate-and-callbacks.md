# ADR 0008 — Telegram reply gate and owner-only approval callbacks

## Status

Accepted

## Context

P8 must drop English keyword request hints that ignored non-English private messages, keep groups mention-only without private tools, and allow Approve/Deny only from the owner private chat (BR-12, INT-TG-02/03).

## Decision

- `needs_reply` silences only multilingual acknowledgements and emoji-only reactions; otherwise private allowlisted DMs get a reply.
- Groups (and non-owner DMs) require an @-mention of the bot; `identity_user_id` stays unset so owner tools stay private.
- Inline keyboard `apr:{id}:{approve|deny}`; callbacks accepted only when `chat_id == sender_id > 0` and the chat is allowlisted; channel `telegram_private`. Duplicate decides are idempotent via ApprovalService.
- Reminder/briefing delivery already uses the scheduler `telegram_send` hook when the channel includes telegram.

## Consequences

- Arabic/French/Spanish (and other) private messages are answered unless they are pure acks.
- Spoofed group callbacks cannot approve; dashboard and owner DM remain the only deciding surfaces.
