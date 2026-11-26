---
name: plan-my-time
description: Find free calendar slots for focus or meetings and create an event only after approval.
version: 1.0.0
metadata:
  compass:
    workflow: W3
    tags: [calendar, focus, schedule, free, slots, meeting]
    tool_groups: [google]
---

# Plan my time

## When to use

The owner asks to find focus time, free slots, or schedule a meeting on the
calendar.

## Procedure

1. Call `google_calendar_list` if context about existing events helps.
2. Call `google_calendar_find_free_slots` with `time_min`, `time_max`, and
   `duration_minutes` from the request (owner timezone).
3. Propose up to three concrete slots in plain language.
4. On owner confirmation, call `google_calendar_create` and wait for approval.
5. Report the Verification fields.

## Stop conditions

- No free slots in range: Nothing to do — say so and offer a wider range.
- Google calendar unavailable: Halted.
- Ambiguous duration or window: ask one short clarification before tools.

## Never

- Invent free slots the find-free tool did not return.
- Create or update events without approval.
- Delete events unless the owner clearly asked (then `google_calendar_delete_event`
  with approval).

## Verification

| Field | Source |
| --- | --- |
| `slots` | `google_calendar_find_free_slots` |
| event_id | `google_calendar_create` when created |
| `outcome` | `awaiting_approval`, `done`, `halted`, or `nothing_to_do` |
