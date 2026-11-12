# AURA Phase 1 / P5 — Today, onboarding, chat cards

**Date:** 2026-11-12  
**Status:** Implemented  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P5** (UX-01..05, 07..10)

## Goal

Make AURA open on a clear **Today** home: one place to ask, approve, see due work, and finish a real getting-started checklist. Add Inbox, Help / How to use, first-run wizard, and richer chat cards — without restyling the design system.

## Scope

- Nav: **Today**, Chat, **Inbox**, Tasks, Memory, Connections, Activity, Settings (hide Automations until P6)
- **Today** at `/`: greeting, composer + four suggested prompts, needs-approval cards, due/overdue tasks, agenda stub (empty until calendar events), getting-started checklist, connection health
- **Inbox** at `/inbox`: pending approvals (shared `ApprovalCard`), empty/loading/error
- **First-run wizard**: name + timezone (+ optional skip); marks wizard complete; checklist appears on Today
- Checklist items complete only after real actions (ask AURA, create task via chat, approve, save memory, connect Telegram or skip briefing for now)
- Help panel (per-screen) + `/help` How to use (five workflows)
- Chat cards: task, approval (existing), receipt; draft / calendar proposal when tool output matches
- Loading / empty / error on new screens; Playwright: new user completes checklist path (or progresses it)

## Out of scope

- Automations / scheduler / daily briefing content (P6)
- Full Google draft/calendar tooling expansion (P7)
- Part 4 design-system rebuild (U0–U3 already assumed)

## Decisions

1. **Today replaces Overview** at `/`; Overview label removed.
2. **Checklist state** lives on owner profile JSON (`onboarding` fields) via `/api/profile` / `/api/onboarding` — no silent mock completion.
3. **Agenda** shows empty state with “Connect Google” until calendar list exists; no invented events.
4. **Suggested prompts** adapt to connected Telegram/Google; always include a generic ask and a remember prompt.
5. **Inbox** is approvals-first (reminders/suggestions tabs as empty placeholders until P6).
