# ADR 0010 — Offline eval harness and lightweight tracing

## Status

Accepted

## Context

P10 (OBS-01..05) needs ≥25 agent scenarios in CI, a pass-rate badge, OpenTelemetry-compatible spans with a trace id per run, an extended `/api/health`, and Activity run detail plus CSV export. Pulling a full OTel SDK would add packaging weight for a thin console exporter.

## Decision

- Store scenarios as JSON under `backend/tests/evaluation/scenarios/` and run them through a scripted `FakeProvider` harness (no network).
- Generate W3C-like `trace_id` values in application code; persist them on `agent_runs`; bridge run events to GenAI-named spans via an in-repo `Tracer` with `none` | `console` exporters (`TRACE_EXPORTER`).
- Extend `/api/health` with database ping, provider probe, worker heartbeat, and last scheduler tick (from `scheduler.tick` audit).
- Activity drawer loads `/api/runs/{id}` when `details.run_id` is present; CSV export is `/api/activity/export.csv`.

## Consequences

- CI keeps evals offline and fast; a manual `evals-live.yml` workflow is ready for a live key.
- Token counts remain optional until providers report them; latency comes from run timestamps and step `duration_ms`.
- An OTLP exporter can implement the same `SpanExporter` protocol later without changing ChatService.
