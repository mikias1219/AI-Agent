# AURA Speed + Clarity Polish

**Date:** 2026-11-11  
**Status:** Approved — implementation complete  
**Approach:** 1 — Fast lists + clarity polish  

## Goal

Make Google lists load quickly, notifications readable, and Telegram status/activity obvious—without new pages or ops ceremony.

## Decisions

| Topic | Decision |
| --- | --- |
| Scope | Speed + clarity together |
| Notifications | Title + labeled fields (no JSON) |
| Gmail | Important ≤100; fetch **current page only**; parallel metadata |
| Calendar/Drive | Keep single list call; paginate in window |
| Telegram | One status card + plain activity / clear empty state |

## Architecture

- `GoogleApiClient.list_gmail`: request `maxResults=page_size` with offset via pageToken walk or fetch window once cached… **Prefer:** fetch Important list up to 100 ids once per request is still heavy—**instead** walk pageTokens only until `start+page_size`, then parallel GET metadata for that chunk only; `total` = min(100, known count or estimate from nextPageToken).
  - Practical algorithm: accumulate message refs with pageToken until `len(refs) >= page * page_size` or no token or 100; `total` = len(refs) if no more token else max(len(refs), page*page_size) capped 100; detail only `refs[start:start+page_size]` in parallel (ThreadPoolExecutor or httpx concurrent).
- Notifications drawer: map `tool_name` → title; pick fields (`to`, `subject`, `body` truncated, `chat_id`, `text`, `title`, `starts_at`) as labeled rows.
- Telegram status panel: Connected / Not connected; Acting as you / Waiting; hide bot-token/allowlist jargon from primary view (optional one-line “Allowlisted chats: N”); activity labels in plain English; empty state copy as approved.

## Out of scope

Server-side cache layer; redesign of whole shell; Telegram pairing UI.

## Success

Gmail page feels snappy; approvals readable; Telegram page answers “connected?” and “anything happening?” at a glance.
