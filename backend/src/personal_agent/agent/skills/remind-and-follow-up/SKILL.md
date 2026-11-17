---
name: remind-and-follow-up
description: Create a durable reminder at a resolved local time and confirm it to the owner before relying on delivery.
version: 1.0.0
metadata:
  aura:
    workflow: W4
    tags: [remind, reminder, follow-up, tomorrow]
    tool_groups: [reminders]
---

# Remind and follow up

## When to use

The owner asks to be reminded at a time, to follow up later, or to list or
cancel reminders.

## Procedure

1. Resolve the when in the owner's timezone (ask once if ambiguous).
2. Call `reminder_create` with a clear title and the resolved time.
3. Confirm the scheduled local time back to the owner.
4. To inspect: `reminder_list`. To cancel: `reminder_cancel` with the id.
5. Report Verification fields.

## Stop conditions

- Time cannot be resolved: Halted — ask for a concrete time.
- Reminder tools unavailable: Halted.

## Never

- Claim a reminder will fire without a successful `reminder_create` result.
- Invent reminder ids.
- Bypass quiet hours policy when the product enforces it for delivery.

## Verification

| Field | Source |
| --- | --- |
| reminder_id | `reminder_create` |
| fire_at_local | resolved owner timezone |
| `outcome` | `done` or `halted` |
