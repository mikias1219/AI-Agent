# AURA Agentic End-to-End

**Date:** 2026-11-10  
**Status:** Draft — pending user review  
**Approach:** 1 — Extend existing ToolRegistry + ApprovalGateway  
**Scope:** Agent Google + Telegram tools, write-only approvals UX, shell/profile/runtime cleanup, Telegram connection UX (not ops)  
**Builds on:** Google OAuth/read APIs (`2026-11-10-aura-google-backend`), Next.js shell (`2026-11-10-aura-nextjs-ui-redesign`)

## Goal

Make AURA act as the user’s agent end-to-end: chat (and inbound Telegram) can use Google and Telegram for real work, writes require clear approval, and the product UI shows connection + action—not start/stop/verify procedures.

## Decisions locked

| Topic | Decision |
| --- | --- |
| Google | Full act: read + write within current OAuth scopes |
| Approvals | Write actions only; reads auto-run |
| Approval UX | Clear pending actions in header notifications (+ existing Tasks path) |
| Profile | Header `ProfileMenu` only; remove sidebar profile block |
| Runtime/model | Chip under chat composer only (from `/api/status`) |
| Telegram | Connected + agent acts as you; no Start/Stop/Verify primary UX |
| Architecture | Approach 1: register tools on existing registry/approvals |

## Out of scope

- In-app Telegram pairing or editing `TELEGRAM_ALLOWED_CHAT_IDS` in the UI
- New Capabilities service layer (Approach 2)
- Generic HTTP tool calling dashboard APIs (Approach 3)
- LinkedIn / Facebook agent tools
- Expanding Google OAuth scopes (no Drive write; no new Gmail/Calendar scopes)
- Production secret / deploy cutover changes

## Architecture

One Agent loop; three tool families on `ToolRegistryImpl` + `DEFAULT_POLICY` + `ApprovalGatewayImpl`:

| Family | Auto (read) | Approval (write) |
| --- | --- | --- |
| Tasks | `task_list` | `task_create`, `task_update_status` (existing) |
| Google | list/get Gmail, Calendar, Drive | send/compose mail; create/update calendar events. **Drive stays read-only** (current OAuth is `drive.readonly`; no scope expansion in this wave) |
| Telegram | list recent activity / chats the agent may use | send message (allowlist enforced) |

```text
Chat or Telegram inbound
  → Agent.select_tools / registry.execute
  → read: run immediately
  → write: prepare → pending approval → user approve/reject → execute or cancel
  → result into same conversation (web stream or Telegram reply)
```

Google credentials: existing `GoogleConnectionStore` + clients.  
Telegram: existing client + allowlist; worker **auto-starts when token and allowlist are configured**. Dashboard start/stop/verify are not the product path (may remain as low-level API for debug).

## Components

### Backend

| Piece | Responsibility |
| --- | --- |
| `application/tools/builtins/google.py` | Wrap Google store/clients; Gmail/Calendar writes approval-gated; Drive read-only tools only |
| `application/tools/builtins/telegram.py` | Activity/list + send; send approval-gated; allowlist hard-fail |
| `app/container.py` | Register Google + Telegram tools beside task/datetime tools |
| Telegram worker lifecycle | Auto-start when configured; no requirement for UI Start/Stop |
| Approvals API | Unchanged contract; new write tools appear as pending items |

### Frontend

| Piece | Change |
| --- | --- |
| `app-sidebar.tsx` | Remove footer profile (avatar/name/email) |
| `profile-menu.tsx` / header | Sole profile surface |
| Chat composer area | Runtime/model chip from `/api/status` |
| `notifications-drawer.tsx` | Live pending approvals; approve/reject; drop mock-first list |
| Telegram page | Connected / Acting as you + recent agent activity; remove Start/Stop/Verify and procedure onboarding as primary UI |
| Overview / capabilities copy | Google live when connected; remove stale “Preview” mismatch |

## Data flow

1. User message in `/chat` or inbound Telegram → same Agent.
2. Tool selection → registry prepare/execute.
3. Write → pending approval; turn surfaces that an action is waiting.
4. Header badge + notifications list tool, short summary, target; Approve executes once with stored args; Reject cancels and informs the agent.
5. Success/failure returns into the active conversation.

## Error handling

| Case | Behavior |
| --- | --- |
| Google not connected | Tool error → agent tells user to connect Google under Connections |
| Telegram not configured or empty allowlist | Tools unavailable → agent + page show not ready / not connected |
| Google token expired | Refresh once; if still failing → ask reconnect |
| User rejects write | Agent acknowledges; no execute |
| Send to non-allowlisted Telegram chat | Hard fail; no send |
| Worker already running in another process | Auto-start no-ops; status still drives “acting/listening” |

## Testing

- Unit: Google/Telegram tools — read executes; write gates on approval; allowlist/not-connected errors
- API: approve/reject executes write once or cancels
- FE: single profile in header; runtime chip under composer; Telegram page has no Start/Stop/Verify primary controls; notifications show live approvals
- Smoke: connected Gmail list from chat; send mail / Telegram message requires approval then succeeds

## Success criteria

- From chat, agent can read Google data when connected and propose writes that require approval before they happen.
- From chat, agent can send Telegram (allowlisted) only after approval.
- Telegram page answers “am I connected / is the agent acting?” without ops ceremony.
- One profile control (header); runtime visible under chat; notifications are real approvals.
- Overview/capabilities no longer claim Google is Preview when the API is live.

## Implementation order (for plan)

1. Shell: remove sidebar profile; runtime chip under composer; fix Overview/Google Preview copy.
2. Notifications: wire live approvals approve/reject.
3. Backend Google agent tools + tests.
4. Backend Telegram agent tools + auto-start lifecycle + tests.
5. Telegram page UX simplification.
6. End-to-end smoke against connected Google + Telegram.
