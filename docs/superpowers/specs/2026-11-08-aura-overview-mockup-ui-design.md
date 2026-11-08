# AURA Overview Mockup UI Design

**Date:** 2026-11-08  
**Status:** Approved  
**Approach:** A — Exact mockup layout/visuals; live API data only

## Goal

Rebuild the authenticated shell and Overview page to match the provided AURA dashboard mockup (left nav, top bar, center bento, right status column, dark violet glass aesthetic) while displaying only real backend data or explicit unavailable/offline states.

## Non-negotiable data rules

- No fake Worker Online, invented task counts, goal %, events, or activity.
- Worker always **Not connected yet** / Offline until Phase 3.
- Hermes/Ollama status from `/api/status` (`active_runtime`, `ollama_reachable`, `hermes_installed`).
- Tasks, approvals, activity, Telegram configured state from existing APIs.
- Missing modules (calendar, goals progress, knowledge folders, email) show Unavailable / Coming later.

## Shell

- Left sidebar: AURA brand, flat module list matching mockup order, Privacy First card, profile from auth.
- Approvals is its own nav item (routes to tasks page focused on approvals or `#approvals` alias).
- Telegram remains reachable via Integrations (and existing `#telegram` route); not required in primary mockup list.
- Top bar: search field (UI only), Worker Offline pill, approvals bell badge (real count).

## Overview

- Greeting with real name + time-of-day.
- Four stat tiles: open tasks (real); events/goals/projects unavailable.
- Agent ask card → existing chat send.
- My Tasks list from real tasks.
- Goals / Knowledge / Integrations cards with honest placeholders; Telegram connection from status.
- Right column: system status, events unavailable, recent activity, CTA to My Agent.

## Out of scope

New APIs, working ⌘K search, theme toggle persistence, worker connectivity, pixel-perfect stock photography (use CSS/gradient substitutes where assets are missing).
