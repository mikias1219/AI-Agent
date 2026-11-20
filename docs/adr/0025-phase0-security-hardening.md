# ADR-0025: Phase 0 security hardening

## Status

Accepted

## Context

The transformation audit found Google OAuth state was a constant, MCP stdio ran with the full
server environment in production, MCP "read-only" trusted every tool on the server, private MCP
HTTP URLs were not blocked, and `/internal/tick` fell back to the dashboard session key.

## Decision

- Google OAuth `state` is a signed, expiring, single-use token that carries the read-only choice.
  The callback stays public because production redirects land on the API host without the Vercel
  session cookie. PKCE is deferred until it can be tested against the live Google client.
- Production MCP: stdio is off unless `MCP_ALLOW_STDIO=1`. Stdio child processes get a stripped
  environment. Private or local HTTP MCP URLs are refused. Tools are `execute` unless both the
  server is marked read-only and the tool declares `annotations.readOnlyHint = true`.
- Production tick requires `INTERNAL_TICK_SECRET` and never falls back to `DASHBOARD_SECRET_KEY`.
- Browser-origin allowlist (S5): deferred. Removing the Vercel preview regex may lock the owner
  out until `FRONTEND_ORIGIN` is confirmed. Impact is Low while the cookie is SameSite=Lax.

## Consequences

Existing production stdio MCP servers show a blocked reason until HTTP is used or the flag is set.
`INTERNAL_TICK_SECRET` must be set as a repository secret before the next deploy or the tick job
fails. OAuth reconnect is required after deploy so old `ro=0`/`ro=1` states stop working.
