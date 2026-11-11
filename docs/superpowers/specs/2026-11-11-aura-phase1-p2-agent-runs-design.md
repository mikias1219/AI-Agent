# AURA Phase 1 / P2 — Agent Runs and Events

**Date:** 2026-11-11  
**Status:** Approved — implementing (full-roadmap sequential)  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P2** (AGT-01..04, 08; OBS-01)

## Goal

Every agent turn is a persisted `AgentRun` with streamed step events, cancel, prompt version, and BR-09 limits — so Chat can show a live tool trail and Stop.

## Scope

- Domain: `AgentRun`, `RunStep`; EventSink port
- Persist steps; events: run.started, token, tool.started/finished, approval.*, run.completed/failed
- API: POST/GET `/api/runs`, events stream, cancel; keep `/api/chat` working
- Prompts in `backend/src/personal_agent/prompts/` with version id
- UI: step trail under answers + Stop button

## Out of scope

Durable approval pause/resume rewrite (P3), Memory, Today shell, scheduler.
