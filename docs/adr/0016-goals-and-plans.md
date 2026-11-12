# ADR 0016 — Goals and plans

## Status

Accepted (full mockup, Task 5)

## Context

The Goals page was a stub and the Chat plan card had a disabled Approve button. Spec §9.2
asks for Goal, Plan and PlanStep entities where approving a plan never widens what the agent
may do on its own.

## Decision

- Proper tables (`goals`, `plans`, `plan_steps`, migration `20261112_08`), domain entities in
  `domain/goals.py`, `GoalService` / `PlanService` in the application layer.
- Approving a plan (`POST /api/plans/{id}/approve`) authorizes `read` and `prepare` steps only.
  `execute` and `destructive` steps become `needs_ok` and still pass the ToolRegistry approval
  gate when they run; approval itself never runs a tool.
- A step's access kind is never lower than its tool's registered kind, at propose time and
  again at approve time, so a model cannot downgrade a hard ceiling by mislabelling a step.
- Tools `goal_create` (result_type `task`) and `plan_propose` (result_type `plan`) are
  `prepare` tools registered through the registry; both have eval scenarios.
- `TodayService` lists active goals from the goal store.

## Consequences

- No plan executor yet: approved read/prepare steps are recorded as authorized, not run.
- Restart-resume of a running step is deferred until an executor exists.
