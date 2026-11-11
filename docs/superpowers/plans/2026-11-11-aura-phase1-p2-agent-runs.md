# P2 Agent Runs Implementation Plan

> **For agentic workers:** subagent-driven-development or executing-plans.

**Goal:** Persist AgentRun/RunStep, emit event stream, cancel, versioned prompts, Chat step trail + Stop.

**Architecture:** Domain models + ports; Agent.run_turn uses EventSink; new run API alongside chat; FE consumes events for trail.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-11-aura-phase1-p2-agent-runs-design.md`
- Keep `/api/chat` until UI fully on runs
- BR-09: max 6 tool rounds / 90s with progress summary
- Offline tests; no secrets; do not implement P3–P8 here

### Task 1: Domain + migration + EventSink

- [ ] AgentRun, RunStep models/ports/repos/migration
- [ ] EventSink protocol + in-memory/list sink for tests
- [ ] Commit `feat(agent): AgentRun and RunStep persistence`

### Task 2: Wire Agent.run_turn + limits + prompts

- [ ] Emit events through sink; persist steps
- [ ] Move system prompt to `prompts/` with version (date, tz, language)
- [ ] BR-09 limits with summary
- [ ] Tests: event order, limit summary, prompt version on run
- [ ] Commit `feat(agent): run events, limits, and versioned prompts`

### Task 3: Runs API

- [ ] POST/GET runs, GET events (SSE or NDJSON), POST cancel
- [ ] Chat path creates/uses runs under the hood or dual-write
- [ ] Commit `feat(api): runs endpoints and cancel`

### Task 4: Chat UI step trail + Stop

- [ ] Show tool steps live; Stop cancels run
- [ ] Commit `feat(ui): chat step trail and stop`

### Task 5: Verify + mark spec Implemented
