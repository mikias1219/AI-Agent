# ADR 0003: Every turn is a persisted AgentRun with an event stream

- Status: Accepted
- Date: 2026-11-11

## Context

P2 (AGT-01..04, AGT-08, OBS-01) needs live tool steps in Chat, a Stop button, BR-09 limits and a
prompt version per answer. The stream only carried text tokens and `/api/chat` kept no record of
what the agent did.

## Decision

- `AgentRun` and `RunStep` are domain models with an `AgentRunRepository` port, tables
  `agent_runs` / `run_steps` and migration `20261111_05`.
- `EventSink` is a domain port. The agent and approval gate publish through `ToolContext.events`
  (`token`, `tool.started`, `tool.finished`, `approval.required`, `approval.resolved`).
  `ChatService` owns the run lifecycle and publishes `run.started`, `run.completed` and
  `run.failed`, so a terminal event is only sent after messages and run status are committed.
  A cancelled run ends with `run.failed` carrying `status: "cancelled"`; no extra event type.
- Tool steps are persisted from the same events (`RunStepRecorder`). Tokens are not persisted:
  live listeners read an in-memory `RunEventBroker`; finished runs outside that window are replayed
  from the stored run and steps (structural events only).
- `ChatService.turn` always opens a run, so `/api/chat`, `/api/chat/stream`, the CLI and Telegram
  all produce runs. `POST /api/runs` runs the turn on a worker thread and returns `202`;
  `GET /api/runs/{id}/events` is NDJSON (matches the existing stream format, works with `fetch`).
- Cancel is cooperative (`CancellationToken`): checked before each model call and before each
  tool, and inside the token callback to abort a streaming call. Skipped tool calls get a
  "Not run" tool message so stored history stays valid. A tool already executing is not interrupted.
- BR-09: defaults 6 tool rounds and 90 s (`RUN_MAX_TOOL_ROUNDS`, `RUN_MAX_SECONDS`). At a limit
  the agent returns a deterministic summary (done, still to do, how to continue) and the run is
  `completed` with `stop_reason` `limit_rounds` or `limit_time`. A single model call is not
  preempted by the time limit; the limit is enforced between steps.
- The system prompt lives in `personal_agent/prompts/system_v1.md`. The stored version is
  `system_v1@<date>/<timezone>/<language>`, rendered from the owner profile in the owner's timezone.
- Streaming is only requested from providers when someone listens or can cancel, because a
  failed stream cannot be retried.

## Consequences

- Durable approval pause/resume (`awaiting_approval`, restart survival) is P3; the status exists
  but is not produced yet. A run that is still `running` when the process dies stays `running`.
- Token counts (AGT-01) and per-run cost (OBS-01) are not captured; providers do not report them
  yet. Timings are stored per step.
- Prompt wording changes require a new `system_vN.md` and a bump of `CURRENT_SYSTEM_PROMPT`.
