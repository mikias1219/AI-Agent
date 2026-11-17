# ADR 0023 — Agent SOUL and versioned skills

## Status

Accepted (2026-11-17)

## Context

AURA’s system prompt (`system_v1`) stated tone and safety briefly, but had no
git-gated identity document or formal workflow procedures. Selam-New Hermes
harness agents use `SOUL.md`, operating `AGENTS.md`, and `SKILL.md` files with
When / Procedure / Stop / Never / Verification. Proposal items AUT-06 and
AG-MEM-02 call for playbooks; we need a maintainable shipped pack before
owner-editable DB playbooks.

## Decision

- Add `personal_agent.agent` with `SOUL.md`, `AGENTS.md`, and five flagship
  skills (W1–W5) as versioned markdown.
- Load matched skills (max two) plus compact SOUL/AGENTS into the chat and
  briefing system prompts via `compose_procedures`.
- Record procedures in `prompt_version` (e.g. `system_v1+soul@1.0.0+skills:…`).
- Enforce file shape with offline unit tests; tool names in skills must match
  the ToolRegistry built-ins.
- Root `AGENTS.md` remains developer/CI instructions only.
- ToolRegistry, hard ceilings, and approvals are unchanged; skills never execute
  tools themselves.

## Consequences

- Procedure changes are reviewable like migrations.
- Activity can show which skill versions applied to a run.
- Owner-editable Memory playbooks can later reuse the same SKILL.md shape.
- Prompt size grows when skills match; the two-skill cap limits context cost.
