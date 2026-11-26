# Flagship reliability + UI clarity (Approach A)

**Date:** 2026-11-17  
**Status:** Implemented  
**Depends on:** `2026-11-17-aura-agent-soul-and-skills-design.md` (SOUL / skills pack)  
**Goal:** Make W1–W5 feel like real agent work (right tools, real evals, soft plan) and make Chat / Today / Memory Playbooks readable.

---

## 1. In scope

| Area | Outcome |
| --- | --- |
| Skill → tool groups | Skills declare `metadata.compass.tool_groups`; `select_tools` intersects with them after match |
| Soft plan | For multi-commit / inbox / plan-my-time skills, show a short numbered plan before tools |
| Evals | W2–W5 scenarios exercise real registry tool names |
| Chat UI | Running status line (skill / tool); clearer card labels |
| Today UI | Honest source / empty copy for agenda and briefing |
| Memory Playbooks | Shipped skills (API) + owner preference/routine memories |
| API | `GET /api/agent/skills` read-only |

## 2. Out of scope

Full L2 planner/missions, DB playbooks CRUD, Telegram redesign, MCP contracts, changing hard ceilings.

## 3. Agent

### 3.1 Skill metadata

```yaml
metadata:
  compass:
    workflow: W4
    tags: [remind, reminder]
    tool_groups: [reminders]
```

Groups use existing `select_tools` names: `google`, `tasks`, `reminders`, `memory`, `goals`, `web`, `core`.

### 3.2 Selection

`ChatService` / agent loop passes matched skill tool_groups into `select_tools(..., skill_groups=...)`. Intersection with connected eligible set; always keep `core`. No match → today’s behavior.

### 3.3 Soft plan

When matched skill is `inbox-to-action` or `plan-my-time`, or user text clearly needs ≥2 commit-class actions, the agent prepends a brief numbered plan in the first assistant message or a `plan` structured step before tool calls. No new persistence table; optional reuse of `plan_propose` only if already natural — prefer lightweight text + trail event `plan.proposed` if cheap, else assistant text only.

### 3.4 Evals

Confirm `reminder_create.json`, mail/calendar/memory scenarios register real builtins (not only spies). Add/adjust one scenario per W2–W5 if missing against real names.

## 4. UI / API

- `GET /api/agent/skills` → list from `list_skills()`: name, description, version, workflow, tags.
- Memory Playbooks tab: section “Shipped procedures” + “Your notes” (preference/routine).
- Chat: status from run events / matched skill name when present in prompt_version or new event field.
- Today: copy strings for connected/empty/unavailable (no invented events).

## 5. Success

- Remind / memory / mail / calendar turns receive a compact tool set from the matched skill.
- Playbooks tab lists five skill names without mock data.
- Today/Chat empty and running states read clearly.
- Approvals and ceilings unchanged.
