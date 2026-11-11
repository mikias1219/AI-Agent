# AURA Phase 1 / P2 — AgentRun and Events

**Date:** 2026-11-11  
**Status:** Approved — implementing (roadmap continuous)  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P2** (AGT-01..04, 08; OBS-01)

## Goal

Every agent turn becomes a persisted `AgentRun` with streamed step events so Chat can show a live tool trail and Stop can cancel before the next step.

## Scope

- Domain: `AgentRun`, `RunStep`; ports + repos + migration
- Agent emits: run.started, token, tool.started/finished, approval.required/resolved, run.completed/failed
- API: POST/GET runs, GET events (SSE/NDJSON), POST cancel; keep `/api/chat` until UI migrates
- Versioned prompts under `backend/src/personal_agent/prompts/`
- BR-09 limits with progress summary
- UI: step trail + Stop on Chat

## Out of scope

Durable approval pause/resume rewrite (P3), memory, Today, scheduler.
