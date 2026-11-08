# AURA Phase 2 — Hermes + Local Ollama Design

**Date:** 2026-11-08  
**Status:** Approved  
**Approach:** A — Dual-path (Hermes when compatible; otherwise Ollama agent loop)

## Goal

Make local Ollama the only supported inference backend. Use Hermes Agent when it can run against a compatible local endpoint; otherwise fall back to the existing `Agent` + `OllamaProvider` loop with an explicit status reason. Remove OpenRouter as a documented or default production path.

## Decisions

| Topic | Decision |
| --- | --- |
| Agent runtime | Hermes only when selected and compatible; never introduce another agent framework |
| Inference | Local Ollama only; no paid cloud model APIs |
| 64k Hermes gate | Keep for Hermes path; fall back to Ollama agent when unmet |
| OpenRouter | Unsupported; if configured, do not call it — fall back to local Ollama agent |
| Worker / job queue | Out of scope (Phase 3) |
| Render | Must not advertise Hermes+OpenRouter; inference belongs on the local machine |

## Runtime selection

When building the app (`container.build_app`):

1. `provider == "fake"` → `FakeProvider` + `Agent` (`active_runtime=fake`).
2. `provider == "ollama"` → `OllamaProvider` + `Agent` (`active_runtime=ollama_agent`).
3. `provider == "hermes"`:
   - If Hermes is installed (`runtime.json` present), `HERMES_CONTEXT_TOKENS >= 64000`, and the effective base URL is local Ollama (empty override or host localhost/127.0.0.1), use `HermesAgent` (`active_runtime=hermes`).
   - Otherwise use `OllamaProvider` + `Agent` (`active_runtime=ollama_agent`) and set `runtime_reason` (e.g. missing install, context below 64k, non-local/cloud base URL).

Hermes request defaults when overrides are empty:

- Model → `OLLAMA_MODEL`
- Base URL → `{OLLAMA_BASE_URL}/v1` (OpenAI-compatible)
- API key → `"ollama"` (local placeholder)

## Status API

Extend `GET /api/status` (and mirror useful fields on `/api/health` if already public):

- `ollama_reachable` (bool) — lightweight probe of Ollama tags/version endpoint
- `hermes_installed` (bool)
- `active_runtime` — `hermes` | `ollama_agent` | `fake`
- `runtime_reason` — short human-readable string (empty when Hermes path is active as requested)

Frontend sidebar/Overview provider pill should reflect `active_runtime` / `runtime_reason` without inventing worker online state.

## Config and docs

- `.env.example`: default `PERSONAL_AGENT_PROVIDER=ollama` or `hermes` with local comments; no OpenRouter model/URL defaults.
- `render.yaml`: remove OpenRouter `HERMES_BASE_URL`; document that cloud dyno is control-plane oriented (full worker offload is Phase 3). Prefer `ollama`/`fake` semantics on Render for now, or hermes only if somehow local — realistically Render should not run local Ollama; set provider guidance to avoid cloud inference.
- Update `docs/hermes.md`, `docs/deploy.md`, `docs/architecture.md`.

## Tests

- Unit tests for runtime selection matrix (installed/context/base URL).
- Existing Hermes bridge and Ollama tests remain green.
- Live Ollama smoke is optional; if Ollama is down, document skip — do not install new tools.

## Out of scope

- AURA Local Worker, job leases, Supabase Auth/RLS
- Softening Hermes upstream 64k requirement
- New product modules

## Acceptance criteria

1. With `provider=hermes` and incompatible local context, app uses Ollama agent and reports reason.
2. With compatible Hermes+local Ollama config, Hermes path is selected.
3. OpenRouter is not the default and is not called when still present in env.
4. Status exposes runtime fields; UI shows them honestly.
5. Backend unit/integration tests for selection pass; e2e still passes with fake provider.
