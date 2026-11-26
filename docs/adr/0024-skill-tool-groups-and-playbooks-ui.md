# ADR 0024 — Skill tool groups and Playbooks UI

## Status

Accepted (2026-11-17)

## Context

SOUL/skills (ADR 0023) inject procedures into the prompt, but the agent still
received a large connected tool set. Small models pick the wrong tools. Memory
Playbooks showed only preference memories, so shipped W1–W5 skills were invisible.

## Decision

- Skills declare `metadata.compass.tool_groups`; after match, `select_tools` intersects
  eligible tools with those groups (+ core) via `ToolContext.skill_groups`.
- Soft-plan hint is appended for inbox / plan-my-time skills.
- `GET /api/agent/skills` exposes the shipped pack; Memory Playbooks lists them
  above owner playbook notes.
- Chat shows a live status line from `skill.matched` / `tool.started`.

## Consequences

- Matched workflows see a compact, relevant tool set.
- Owners can see what procedures exist without reading the repo.
- Full L2 planner and owner-editable DB playbooks remain future work.
