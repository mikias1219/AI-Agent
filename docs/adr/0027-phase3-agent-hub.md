# ADR-0027: Phase 3 Agent hub (overview, commits, Telegram controls)

Status: Accepted

## Context

Phase 3 of `docs/TRANSFORMATION.md` closes three product gaps: Agent overview (G7), a real daily
commit counter against BR-09 (G5 step one), and Telegram controls including a test message (G10).
Autonomy presets remain truthful-copy-only until Phase 5 (decision D3).

## Decision

1. **Agent destination defaults to Overview** at `/agent`. Memory, Routines, Activity and
   Connections stay as hub tabs. The primary nav and command palette link to `/agent`.
2. **Capabilities** are read-only: `GET /api/agent/capabilities` lists registered tools and counts
   by access kind from the live `ToolRegistry`. The Overview UI maps `execute`/`destructive` to the
   owner-facing word "Commit".
3. **Commit budget** increments only after a successful approved `execute` or `destructive` tool
   finishes. The registry calls an `on_commit` hook wired in `container.py` to
   `AgentControlService.record_commit`. Cap is 20 (`DEFAULT_COMMITS_CAP`, BR-09). Hard ceilings and
   Balanced auto-commit remain Phase 5.
4. **Telegram controls** expose existing start/stop/verify endpoints plus `POST /api/telegram/test`,
   which sends a fixed confirmation string to the first allowlisted chat via `TelegramService`.

## Consequences

- Settings → Permissions and Agent → Overview both show live `commits_used` / `commits_cap`.
- Preset changes still do not alter the permission policy; copy continues to say every send or
  change asks.
- Stdio MCP and CORS (S5) are unchanged from Phase 0.
