# AURA Telegram Agent Clarity

**Date:** 2026-11-11  
**Status:** Implemented  
**Approach:** 1 — Agent guide page (always-on + how it helps + how to use)  
**Builds on:** `2026-11-11-aura-ux-lists-markdown-telegram-design.md`, production UX review

## Goal

Make Telegram feel like **the user’s always-on personal agent**, not a connection ops panel. A user opening `/connections/telegram` should know within ~10 seconds: (1) how it helps them, (2) how to message the bot, (3) whether it is listening, (4) where to see that it replied.

## Decisions locked

| Topic | Decision |
| --- | --- |
| Runtime | **A — Always listening** (lifespan auto-start; no start/stop/verify in UI) |
| Page job | Teach value + usage + one honest status |
| Status vocabulary | Shared four states only: **Listening** / **Starting** / **Needs setup** / **Error** |
| Reply policy | Unchanged: questions/requests get replies; casual “ok/thanks” stay quiet |
| Overview / health | Same vocabulary as Telegram page (drop “Setup / finish setup”, “Configured”, “Managed · running”) |

## Problem (from production review)

- Status contradicts itself: **Connected · waiting** + **Status: Stopped**
- Overview says **Setup — Configured — finish setup** while the Telegram page looks connected
- Page never explains **how it helps** or **how to use** the agent
- Activity shows raw chat IDs; empty/first-use path is weak
- User does not know Telegram is their agent outside the dashboard

## Out of scope

- Start / Stop / Verify buttons
- Keyword or rules admin UI
- Changing `needs_reply` gate policy
- Telegram ↔ Chat transcript sync UI
- LinkedIn / Facebook
- Global Activity heartbeat collapse (optional later; not required for this wave)

## Architecture

```text
Backend lifespan
  → auto-start telegram worker when wired + allowlisted
  → status payload: configured, username, allowed_chat_ids, managed, runtime, last_seen, error

Frontend Telegram page
  → map status → Listening | Starting | Needs setup | Error
  → Status panel (one label + one hint)
  → How it helps (bullets)
  → How to use (3 steps + t.me link + example prompts)
  → Recent activity (human events)

Overview + HealthStrip
  → same four-state mapping as Telegram page
```

## Status mapping

| User state | Conditions (client mapping) | Hint intent |
| --- | --- | --- |
| **Needs setup** | `!configured` OR `allowed_chat_ids.length === 0` | One plain next step for server token / allowlist |
| **Error** | `runtime === "error"` (or equivalent error surface) | Short recovery; check token / try later |
| **Starting** | configured + allowlisted + not yet acting (`starting`, or not managed/`stopped`/`unknown` while auto-start expected) | “Starting your Telegram agent…” |
| **Listening** | configured + allowlisted + acting runtime (`polling`, `responding`, `running`, or `managed` with healthy listen) | “Agent is listening in your allowlisted chats.” |

**Rules:**

- Never show “Connected” together with “Stopped”
- Never show Overview “finish setup” when allowlisted
- Prefer **Listening** as the healthy default after auto-start
- If production often stays **Stopped** despite allowlist, treat as a bug in the same wave (auto-start, foreign-runtime skip, or status `managed` mapping)

## UI — Telegram page

### Header

- Title: **Telegram**
- Subtitle: **Your always-on agent on Telegram — ask here, get help without opening the dashboard.**
- Keep Refresh; keep “All channels” link

### Status panel

- Show bot `@username` when known
- One `role="status"` label from the four states
- One supporting hint (no second conflicting runtime line like “Status: Stopped” under “Connected”)
- Allowlisted chat count as secondary meta when connected enough to listen/setup-complete

### How it helps you

Always visible when status is loaded (especially when Listening):

- Answers questions in Telegram the same way as Chat
- Can check Important email and upcoming calendar when Google is connected
- Can create tasks; write actions still need approval in the dashboard
- Stays quiet on casual “ok / thanks”; replies when you ask for something

### How to use

1. Open Telegram and message **`@{username}`** (deep link `https://t.me/{username}` when username present; fallback plain text if missing)
2. Ask a real request (examples below)
3. Return here to see **Agent replied** / **Skipped** under Recent activity

**Example prompts** (static chips or plain list — not send actions):

- What’s on my calendar today?
- Any important email I should see?
- Create a task to follow up on CI

### Recent activity

- Keep existing event labels (`Agent replied`, `Skipped (no reply needed)`, etc.)
- Prefer message preview over raw chat id when preview exists
- Empty state: ask a question in Telegram first (aligned with How to use)

## UI — Overview + health strip

| State | Overview tile value | Overview detail | Health chip |
| --- | --- | --- | --- |
| Listening | Listening | Agent replies in Telegram | Listening |
| Starting | Starting | Starting your Telegram agent | Starting |
| Needs setup | Needs setup | Open Telegram page | Needs setup |
| Error | Error | See Telegram page | Error |

## Backend

- Keep `should_autostart_telegram` + lifespan `worker.start` when allowlisted
- No new control endpoints required for UI
- Fix or verify: after deploy, allowlisted workspaces reach Listening (not stuck Stopped / non-managed while UI claims ready)
- Status fields already used by FE remain the source of truth; FE owns user-facing vocabulary

## Files (expected)

| Area | Likely touch |
| --- | --- |
| FE | `telegram-page.tsx`, `telegram-status-panel.tsx`, shared status helper if useful |
| FE | `overview-page.tsx`, `health-strip.tsx` |
| FE | `format.ts` only if activity detail needs small cleanup |
| BE | `app.py` lifespan / status only if auto-start or `managed` mapping is wrong in prod |
| Tests | FE unit/mapping if present; BE autostart/status tests if touched |

## Success criteria

1. No contradictory Telegram status copy on page or Overview
2. User can explain how Telegram helps them and how to message the bot without leaving the page
3. Healthy prod state shows **Listening** when the worker is up
4. Reply-gate behavior unchanged
5. No start/stop/verify controls added

## Spec self-review

- No placeholders left for product decisions
- Status vocabulary is single-sourced in this doc for Overview + Telegram
- Scope excludes ops controls and reply-policy changes
- Always-on + teaching UI are both in scope; backend work limited to making Listening true
