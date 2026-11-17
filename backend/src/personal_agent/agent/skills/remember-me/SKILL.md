---
name: remember-me
description: Save, search, or forget owner preferences and facts through memory tools with clear confirmation.
version: 1.0.0
metadata:
  aura:
    workflow: W5
    tags: [remember, memory, preference, forget]
    tool_groups: [memory]
---

# Remember me

## When to use

The owner asks to remember a preference or fact, to recall what you know, or to
forget something saved earlier.

## Procedure

1. For save: call `memory_save` with a concise fact. Prefer confirmation when the
   product shows a Save chip; do not invent extra facts.
2. For recall: call `memory_search` (or rely on already recalled facts in context)
   and cite them as Used memory when they shape a suggestion.
3. For forget: call `memory_forget` with the id, or `memory_forget_all` only when
   clearly requested.
4. Report Verification fields.

## Stop conditions

- Empty or vague memory text: ask one short clarification.
- Forget without a clear target: Halted — list candidates via search first.

## Never

- Treat a memory as permission to skip approvals or hard ceilings.
- Claim a memory was saved or deleted without a successful tool result.
- Store secrets (passwords, API keys) as memory.

## Verification

| Field | Source |
| --- | --- |
| memory_id | memory tool |
| `action` | `save`, `search`, or `forget` |
| `outcome` | `done` or `halted` |
