# Google Backend Wave Implementation Plan

> **For agentic workers:** Use subagent-driven-development or execute inline. Steps use checkboxes.

**Goal:** Real Google OAuth + Gmail/Calendar/Drive lists for the Next.js UI.

**Architecture:** Seal tokens in `GoogleConnectionStore`; httpx clients for Google APIs; FastAPI routes; frontend `lib/api/google.ts`.

**Tech Stack:** FastAPI, httpx, SQLAlchemy, Next.js

## Global Constraints

- Never commit `GOOGLE_CLIENT_*` or tokens
- Do not change production Render/Vercel secrets in this wave
- Match frontend Message/Event/File field names exactly (camelCase in JSON)

### Task 1: Spec + worktree

- [x] Spec and plan written under docs/superpowers
- [x] Branch `feature/aura-google-backend` worktree

### Task 2: OAuth tokens

- [ ] Token seal helpers
- [ ] Store save/load tokens + email
- [ ] OAuth exchange/refresh/revoke via httpx
- [ ] Wire callback/connect/disconnect; remove local fake-connect
- [ ] Unit/integration tests with mocked httpx

### Task 3: List APIs

- [ ] Gmail/Calendar/Drive clients + paginated routes
- [ ] Tests with mocked Google responses

### Task 4: Frontend wire

- [ ] `lib/api/google.ts`
- [ ] Google page uses API when capability is api
- [ ] `capabilities.google = "api"`

### Task 5: Browser OAuth setup

- [ ] Google Cloud Console OAuth client + local `.env`

### Task 6: Docs + review

- [ ] Update deploy.md Google section
- [ ] Fix review findings
