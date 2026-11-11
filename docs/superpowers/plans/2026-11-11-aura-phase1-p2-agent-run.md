# P2 AgentRun Implementation Plan

> **For agentic workers:** subagent-driven-development or executing-plans.

**Goal:** Persist AgentRun/RunStep, emit event stream, cancel, versioned prompts, Chat step trail + Stop.

**Architecture:** Domain models → repos → Agent.run_turn EventSink → API SSE → Chat UI.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-11-aura-phase1-p2-agent-run-design.md`
- Keep `/api/chat` working; add `/api/runs*` alongside
- Offline tests; no durable approval rewrite (that's P3)

### Task 1: Domain + migration AgentRun/RunStep
### Task 2: EventSink in Agent.run_turn + limits + prompts version
### Task 3: API runs + events + cancel
### Task 4: Chat UI step trail + Stop
### Task 5: Verify + mark implemented
