# AURA Phase 1 / P1 — Task Model

**Date:** 2026-11-11  
**Status:** Implemented  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P1** (TSK-01, 03, 04, 06; BR-06, BR-11)  
**Roadmap:** Sequential full proposal — after P0; before P2 AgentRun

## Goal

Tasks become real commitments: due dates, priority, project/tags, search/views, plain-language quick add with timezone-aware dates, and soft delete — without building reminders/scheduler yet.

## Scope

| ID | Deliverable |
| --- | --- |
| TSK-01 | Fields: notes (alias description), priority (p1/p2/p3/none), due_at, project, tags, source, source_ref, completed_at |
| Profile | `owner_profile`: owner_id, name?, timezone, language |
| Tools | Extended create; update; search; reopen; delete (destructive soft) |
| Dates | Relative date resolution in owner timezone |
| API | `view=today\|upcoming\|overdue`, filters, search |
| UI | Views, quick add, badges, detail drawer, empty/error |

## Out of scope (later prompts)

Reminders (P6), AgentRun (P2), durable approvals (P3), Memory/Today (P4/P5), MCP, Google expansion.

## Success

Section 16 Tasks scenario; planned→done already from P0; create with due/priority; views filter correctly; soft-deleted tasks hidden from default lists.
