# ADR-0028: Phase 4 Initiative (suggestions, routines, mail triage, plan executor)

Status: Accepted

## Context

Phase 4 of `docs/TRANSFORMATION.md` closes G1–G4: the agent must take bounded initiative
without bypassing the registry gate. Suggestions, routines, mail replies and plan steps already
had shells; they lacked producers and executors.

## Decision

1. **`suggestion_propose`** is a `prepare` tool that calls `SuggestionService.create` with a
   mandatory source citation. Open suggestions are capped (default 5). Accept still runs through
   `ToolRegistry.execute`.
2. **Briefing** may create at most two follow-up suggestions from real briefing sections
   (`email` / `tasks` / `approvals`) after a successful build.
3. **Routine catalogue** seeds five kinds via `DEFAULT_AUTOMATION_SEEDS`: morning briefing
   (enabled), inbox triage, evening wrap-up, weekly review, deadline guard (disabled). Owners
   enable/disable and schedule; no free-form builder.
4. **Inbox triage** and **deadline guard** use deterministic handlers that only read live data
   through the registry (or task store) and create suggestions. Other kinds use a bounded agent
   turn with a catalogue prompt.
5. **Mail replies** are suggestions with `kind=mail_reply`, shown on Needs you → Mail replies.
   Proposed action is typically `google_gmail_reply`; sending still needs approval (BR-05).
6. **Plan approval** authorizes read/prepare steps as before, then `PlanExecutor.run_authorized`
   runs those steps through the registry in dependency order. Execute/destructive steps stay
   `needs_ok`.

## Consequences

- Enabling Inbox triage without Google connected records a skip summary, not invented mail.
- Approving a plan may immediately call tools (read/prepare only); the UI must refresh step
  statuses after approve.
- Presets and hard ceilings remain Phase 5 (decision D3).
