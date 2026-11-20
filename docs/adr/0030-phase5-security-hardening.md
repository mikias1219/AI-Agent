# ADR-0030: Phase 5 light security hardening (S8–S12)

Status: Accepted

## Context

`docs/TRANSFORMAT.md` lists S8–S12 as Phase 5 follow-ups after trust/data work.

## Decision

1. **S8 Rate limits** — `SlidingWindowRateLimiter` on `/api/chat`, `/api/runs` and MCP
   mutate/discover endpoints (`API_RATE_LIMIT_PER_MINUTE`, default 120). Concurrent runs
   capped via `MAX_CONCURRENT_RUNS` (default 2) on `POST /api/runs`.
2. **S9 Health** — unauthenticated `GET /api/health` returns `{status: "ok"}` only.
   Authenticated sessions still receive the full probe payload.
3. **S10 CSV** — activity CSV cells are passed through `csv_safe_cell` (prefix `'` when the
   value starts with `=`, `+`, `-`, `@`, or a control character).
4. **S11 Login lockout** — failures persist in `data/login_lockout.json` (survives restart).
5. **S12 Frontend headers** — Next.js `headers()` adds CSP, Referrer-Policy, X-Frame-Options,
   Permissions-Policy, and HSTS in production; FastAPI already sets CSP/nosniff/frame and now
   also Referrer-Policy + HSTS in production.

## Consequences

- Load balancers can still probe `/api/health` without leaking provider/model details.
- S6 (token encryption at rest) closed in ADR-0032.
