# AURA UX: Lists, Markdown, Tasks, Selective Telegram

**Date:** 2026-11-11  
**Status:** Approved — implementation complete  
**Approach:** 1 — Fix product path in place  
**Builds on:** `2026-11-10-aura-agentic-e2e-design.md`

## Goal

Make daily use trustworthy and simple: Important Gmail and upcoming Calendar list correctly with pagination; chat replies read as formatted text; agent-created tasks show on Tasks; Telegram replies only when the message needs a response.

## Decisions locked

| Topic | Decision |
| --- | --- |
| Gmail | `is:important` only; recent window **≤100**; UI pagination within that window |
| Calendar | **Upcoming only** (`timeMin=now`); ≤100; paginated |
| Chat | Light Markdown for **assistant** bubbles only |
| Tasks | Agent creates under workspace owner `dashboard`; Tasks page shows them |
| Telegram | **B** — reply only for question / request / action; silent on casual noise |
| UI | No new hubs or ops panels; same pages, corrected behavior |

## Out of scope

- Full mailbox sync, Primary/Promotions tabs, search UI
- Telegram keyword/rules admin UI
- User-bubble Markdown
- Drive list overhaul
- Expanding OAuth scopes

## Architecture

```text
Connections Google tabs
  → existing /api/google/{gmail|calendar}
  → GoogleApiClient list helpers (corrected query/window)

Chat MessageList
  → assistant content → light Markdown render
  → user content → plain text

Telegram inbound
  → allowlist → commands (/start|/help|/new) always reply
  → reply gate (needs_reply?) → silent audit OR ChatService.turn → send

Tasks
  → task_create uses ToolContext.user_id (dashboard for web + private TG)
  → GET /api/tasks → Tasks page
```

## Components

### Backend

| Piece | Change |
| --- | --- |
| `infrastructure/integrations/google/clients.py` | Gmail: `q=is:important`, cap 100, paginate honestly within window. Calendar: `timeMin=now` (UTC), upcoming, cap 100, paginate. |
| Agent Google list tools | Use same client (no “all mail” path). |
| `telegram_reply_gate.py` (new) | Classify inbound text → `needs_reply: bool` (+ optional reason). |
| `telegram/runner.py` | Call gate before turn; ignore → audit `telegram.ignored_no_reply`; gate failure → reply (fail open). |
| Task ownership | Confirm private Telegram + dashboard use `identity_user_id`/`user_id` = `dashboard` for tools; fix any path that still owns tasks under `telegram:…` when they should appear on the Tasks page. |

### Frontend

| Piece | Change |
| --- | --- |
| `features/chat/message-list.tsx` | Render assistant Markdown (bold, italics, lists, inline code, links). Keep layout simple. |
| Google connections copy | Clarify “Important” / “Upcoming” in page subtitle or tab context if needed. |
| Tasks page | Ensure refresh/load shows latest; no redesign. |

## Data flow

1. **Gmail page N** → list Important messages in the last-100 window → `{ items, page, page_size, total }` with `total ≤ 100`.
2. **Calendar page N** → upcoming events from now → same pagination shape.
3. **Chat** → stream text → assistant bubble Markdown render.
4. **Telegram** → gate → silent or full turn + send.
5. **Task create** → owner `dashboard` → visible on `/tasks`.

## Errors

| Case | Behavior |
| --- | --- |
| No Important mail / no upcoming events | Empty state |
| Google disconnected | Existing 400/agent error |
| Markdown parse issues | Soft fail; readable text still shown |
| Reply gate error | Reply anyway (do not drop real asks) |
| Unauthorized Telegram chat | Existing ignore + audit |

## Testing

- Unit: Gmail query + cap + pages; Calendar timeMin; reply gate positives/negatives; `/start` still replies
- FE: assistant `**bold**` renders; user `**x**` stays literal
- Smoke: Important mail pages; upcoming calendar; task from chat appears on Tasks; casual TG silent, question gets reply

## Success criteria

- Connections Gmail shows Important mail only, up to 100, with working pagination.
- Connections Calendar shows upcoming events, not ancient history.
- Chat assistant replies no longer show raw `**` / list markup as noise.
- Tasks created by the agent appear on the Tasks page for the workspace owner.
- Telegram stays quiet on casual noise and answers questions/requests/actions.
- UI remains the same simple pages—no new control panels.

## Implementation order

1. Google client list fixes + tests  
2. Chat Markdown rendering  
3. Task ownership / visibility check + fix  
4. Telegram reply gate + runner wiring + tests  
5. Light copy polish + smoke  
