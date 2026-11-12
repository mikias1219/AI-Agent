# ADR 0017 — Suggestions and the unified inbox

## Status

Accepted (full mockup, Task 6)

## Context

The Inbox listed approvals, reminders and history in separate tabs, and Today's "Needs you"
only knew about approvals. Spec §9.3 adds suggestions: ideas AURA proposes unprompted. Spec §8
makes Inbox the single home for everything that needs the owner.

## Decision

- `suggestions` table (migration `20261112_09`), entity and rules in `domain/suggestions.py`,
  `SuggestionService` in the application layer.
- Every suggestion must carry a non-empty `source` citation. The domain rejects a blank one;
  nothing defaults or invents a citation.
- Accepting a suggestion with a `proposed_action` (`{tool_name, arguments}`) runs that action
  through `ToolRegistry.execute` (wired in the container), so approval gates and hard ceilings
  still apply. An execute/destructive tool leaves the suggestion `accepted` with outcome
  `pending_approval` and a real approval in the queue; the UI says nothing has happened yet.
  A failed action leaves the suggestion open. A suggestion with no action is only acknowledged.
- Dismiss stores optional feedback. Open suggestions past `expires_at` become `expired` when
  read.
- `GET /api/inbox?tab=open|done` merges approvals and suggestions as items with a `kind`
  (`approval` | `suggestion`); the UI picks the card from `kind`. Open items are ordered by a
  pure domain urgency score: approvals by risk (high 90, medium 70, low 50), suggestions 30,
  plus up to +9 as expiry nears within 24h. `counts.open` is the true open total.
- `TodayService` needs-you takes the top three open inbox items; the sidebar badge uses
  `counts.open`, falling back to the approvals count if the inbox call fails.
- Reminders are no longer a tab in Inbox (still on Routines); the spec only lists
  approvals and suggestions here.

## Consequences

- Nothing creates suggestions yet except the service. A `suggest` tool and proactive
  producers (as real AgentRuns, within quiet hours and the daily cap) are later work.
- The accept action runs outside an AgentRun (origin `suggestion`, no run id); approvals it
  creates are decided on their own and resume no run.
