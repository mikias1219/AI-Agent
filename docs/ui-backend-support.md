# UI ↔ backend support map (mockup UI v2)

Every product screen is backed by a live contract (or an honest empty /
unavailable state). Demo mode uses a separate database; no mock list endpoints
outside demo.

| Screen | Primary APIs | Notes |
| --- | --- | --- |
| Shell (listening, pause, autonomy, bell) | `GET/PATCH /api/agent/control`, `GET /api/inbox`, `GET /api/activity` | Bell is a short list; work stays in Inbox |
| Today | `GET /api/today`, onboarding, `POST /api/runs` cancel | Sections omit when empty; no invented agenda |
| Chat | `GET/POST /api/conversations`, runs + NDJSON events | Cards from `result_type` only |
| Inbox | `GET /api/inbox`, approvals + suggestions | Needs you / Done |
| Tasks | `GET/POST/PATCH /api/tasks?view=` | List + Board; Today/Upcoming/Overdue/All/Done |
| Goals | `GET/POST/PATCH /api/goals`, plan approve/cancel | Live plans only |
| Calendar | `GET /api/google/status`, `GET /api/google/calendar` | Today / Week / Day; Find time → Chat prompt |
| Mail | Gmail list + status | Client buckets; Untrusted banner; never invents messages |
| Memory | `GET/POST/PATCH/DELETE /api/memories`, `/api/memories/proposals*` | Proposed is durable until Save/Dismiss |
| Routines | `GET/PATCH /api/automations`, run-now | Quiet hours + daily_cap on each routine |
| Activity | `GET /api/activity` (+ CSV export) | Chips: All / Chat / Routines / Telegram / Needs review |
| Connections | Google + Telegram status endpoints | Warnings only when broken |
| Settings Appearance | localStorage theme/density | ADR 0021; no server sync yet |
| Settings Permissions | `/api/agent/control` | Presets, pause, budgets |
| First-run wizard | `/api/onboarding/wizard`, `/api/status`, Google status, agent control | Profile → Model → Connect → Autonomy |
| Help | static W1–W6 | No fake live data |

Hard ceilings, pause, and quiet hours are unchanged by UI chrome.
