# AURA Phase 1 / P10 — Evals and observability

**Date:** 2026-11-12  
**Status:** Implemented  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P10** (OBS-01..05)

## Goal

Prove agent quality with ≥25 offline eval scenarios in CI, emit OpenTelemetry-compatible spans with a trace id per run, extend `/api/health`, and surface run steps/latency plus CSV export on Activity.

## Scope

- Scenario format (JSON): input, tools, scripted provider turns, expected/forbidden tool calls, expected text, stop_reason
- `backend/tests/evaluation/` harness + 25 scenarios (OBS-03 list) including injection and group privacy
- CI job for evals; `workflow_dispatch` live-model workflow (scripted skip unless secret set); pass-rate badge SVG script
- Lightweight tracing: generate `trace_id` per run, spans for run + tool steps, exporter `none` | `console` (OTLP optional later)
- Extend `/api/health`: db ok, provider probe, worker heartbeat, last scheduler tick
- Activity: CSV export; run-detail section in drawer when `run_id` present (steps, tokens/latency)

## Out of scope

- Demo mode / README portfolio rewrite (P11)
- Full Langfuse OTLP packaging (console exporter is enough for v1)

## Decisions

1. **Scenarios as JSON** under `tests/evaluation/scenarios/` — no PyYAML dependency.
2. **Tracing** without hard OTel SDK dep: in-repo `Tracer` port; W3C-like 32-hex `trace_id`; spans recorded to audit/console.
3. **Badge:** `scripts/eval_badge.py` writes `docs/badges/eval.svg` from pytest junit/json summary.
