# Flagship reliability + UI clarity Implementation Plan

> **For agentic workers:** Use executing-plans / implement task-by-task.

**Goal:** Skill tool_groups filter, soft plan hint, skills API, Chat/Today/Memory clarity.

**Architecture:** Extend skill metadata + `select_tools(skill_groups=)`; pass groups via `ToolContext`; Memory fetches `GET /api/agent/skills`.

---

### Task 1: tool_groups on skills + select_tools
### Task 2: Wire ChatService → ToolContext → agent
### Task 3: Soft plan hint in compose for inbox/plan skills
### Task 4: GET /api/agent/skills + Memory Playbooks UI
### Task 5: Today/Chat copy clarity
### Task 6: Tests + ADR note / README
