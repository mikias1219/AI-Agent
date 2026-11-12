# P6 Scheduler Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice. Isolated worktree.

**Goal:** Durable jobs, tick endpoint, reminders, daily briefing, Automations UI.

**Architecture:** JobQueue + worker/tick; ReminderService + BriefingService; Automations CRUD.

## Global Constraints

- Spec + proposal P6; BR-07 late label; BR-14 no gate bypass; offline tests
- Do not invent calendar events; empty → “nothing scheduled”
- Do not build P7–P9 here

### Task 1: Schema + JobQueue

- [x] Migration jobs/reminders/automations
- [x] Domain + JobQueue port/adapter
- [x] Tests: enqueue, claim due, idempotency key unique

### Task 2: Tick + worker + reminders

- [x] `/internal/tick` + lifespan worker
- [x] Reminder create/deliver/late; Inbox API
- [x] Tests: duplicate tick once, late label, restart

### Task 3: Daily briefing + Automations UI

- [x] Briefing job → AgentRun origin automation; channels
- [x] Automations screen + nav; ensure default briefing automation
- [x] tick.yml workflow; mark Implemented
