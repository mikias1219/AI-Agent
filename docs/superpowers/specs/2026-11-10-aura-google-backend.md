# AURA Google Backend Wave

**Date:** 2026-11-10  
**Status:** Approved (plan execution)  
**Scope:** Backend Google OAuth + read list APIs; frontend capability flip  
**Out of scope:** LinkedIn/Facebook, notifications, production secret cutover, agent write tools

## Goal

Replace Next.js Google mocks with live APIs so `/connections/google` shows real Gmail, Calendar, and Drive rows after OAuth.

## Decisions

| Topic | Decision |
| --- | --- |
| Wave | Google only |
| APIs | Read lists: gmail, calendar, drive |
| OAuth | Real code exchange + refresh; tokens stored server-side |
| Encryption | At-rest seal with key derived from `DASHBOARD_SECRET_KEY` |
| Frontend | `capabilities.google = "api"` + `lib/api/google.ts` |
| Production secrets | Unchanged until later cutover |

## API contracts

### Existing (behavior change)

- `GET /api/google/status` — unchanged shape; `connected` true only when tokens exist
- `POST /api/google/connect` — returns `{ auth_url }`; does **not** fake-connect in local
- `GET /api/google/callback?code=` — exchange code, store tokens + email, HTML close tab
- `POST /api/google/disconnect` — revoke best-effort + clear tokens

### New

- `GET /api/google/gmail?page=1&page_size=8` → `{ items: Message[], page, page_size, total }`
- `GET /api/google/calendar?page=1&page_size=8` → `{ items: Event[], page, page_size, total }`
- `GET /api/google/drive?page=1&page_size=8` → `{ items: File[], page, page_size, total }`

Shapes match frontend mocks:

- Message: `{ id, from, subject, snippet, receivedAt }`
- Event: `{ id, title, startsAt, location }`
- File: `{ id, name, kind, updatedAt }`

Unauthenticated / not connected → 401 or 400 with clear detail.

## Architecture

- `infrastructure/integrations/google/oauth.py` — token exchange/refresh/revoke
- `infrastructure/integrations/google/clients.py` — Gmail/Calendar/Drive list
- `infrastructure/persistence/hub_store.py` — persist sealed tokens
- Routes in `presentation/web/app.py` (keep colocated with existing google routes)

## Success

Local Connect → callback stores tokens → list tabs show live data; tests pass; no secrets in git.
