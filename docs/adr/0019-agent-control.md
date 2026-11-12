# ADR 0019 — Agent control (pause, autonomy, budgets)

## Status

Accepted (full mockup, Tasks 2, 8, 9)

## Context

The shell needs Pause, Listening, and an autonomy chip. Proactive Telegram must respect
quiet hours and a daily cap. Hard ceilings must never be relaxed by a preset.

## Decision

- Persist control state on `owner_profile.agent_control_json`.
- `AgentControlService` exposes get/patch for `autonomy_preset`, `paused`, and daily budgets.
- `ToolRegistryImpl` blocks non-`read` tools while paused (Chat, Telegram, Routines).
- `proactive_gate` + scheduler skip external proactive sends during quiet hours, when paused,
  or when `proactive_used >= cap`; inbox briefing persistence still runs.
- Settings → Permissions and the first-run wizard set presets; header Pause/Resume is live.

## Consequences

- Presets are UX guidance; hard ceilings still go through approvals.
- Routine-level quiet hours/daily_cap override the global proactive cap when set (>0).
