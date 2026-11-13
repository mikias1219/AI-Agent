# AURA mockup UI v2 (updated board parity)

**Date:** 2026-11-13  
**Status:** Approved in chat — awaiting file review  
**Source mockup:** `AURA — Today v2 and Chat v2 mockups.html` (30 frames)  
**Prior work:** `docs/superpowers/specs/2026-11-12-aura-full-mockup-design.md` (Approach A backend + first UI pass on `main`)  
**Approach:** Full product UI parity (Approach 2) — light + dark, Comfortable/Compact, mobile, bell/profile/autonomy menus; W1–W6 live in Help; Components = shared atoms only  
**Branch:** `feature/aura-mockup-ui-v2`

---

## 1. Goal

Bring the live dashboard to visual and interaction parity with the **updated** mockup board for every product screen, while keeping truth rules: real or honestly unavailable data, cards from `result_type`, pause / quiet hours / hard ceilings unchanged.

## 2. In scope

| Area | Mockup frames | Product outcome |
| --- | --- | --- |
| Tokens + atoms | Components, Color usage | Light + dark CSS vars; chip/button/row/density primitives |
| Shell | App shell, Bell/profile/autonomy menus, Mobile | 248px nav, header chrome, bell drawer, menus, responsive |
| Today | Today v2, Today compact, Today dark, Mobile | Sections + Comfortable/Compact + dark |
| Chat / Inbox | Chat v2, Inbox | Thread list, typed cards, Needs you / Done |
| Tasks / Goals | Tasks, Goals | List + Board; goal detail + plan |
| Calendar / Mail | Calendar, Mail | Week/day; AURA mail buckets |
| Memory | Memory | All / Facts / People / Playbooks / Proposed |
| Routines / Activity / Connections | those frames | Quiet hours UI polish; human activity; broken-only warnings |
| Settings / first-run | Settings — Permissions, First-run autonomy | Appearance (theme), 4-step wizard |
| Help | How AURA works, W1–W6 | Loop + six workflows in Help |
| Modals / lists | Modals, Lists pagination states | Approval/edit modals; pagination patterns |

## 3. Out of scope

- Separate `/components` or `/color` museum routes
- Separate W1–W6 storyboard routes (content folded into Help)
- Inventing calendar/email/task facts for empty states
- Changing ToolRegistry / hard-ceiling / pause semantics
- Telegram native UI redesign beyond documenting channel behavior in Help/Connections
- Re-pushing / redeploying until UI branch is ready (separate from this design)

## 4. Visual system

### 4.1 Light tokens (unchanged roles)

| Token | Hex | Job |
| --- | --- | --- |
| `--canvas` | `#F7F8FA` | Page background |
| `--surface` | `#FFFFFF` | Cards, nav, header |
| `--ink` | `#0F1720` | Primary text |
| `--muted` | `#52606D` | Secondary |
| `--border` | `#E4E7EB` | Rules |
| `--accent` | `#0F766E` | Primary button, active nav, links, focus |
| `--accent-soft` | `#E6F4F2` | Selection |
| `--success` | `#15803D` | Done / listening / connected — never primary buttons |
| `--warning` | `#B45309` | Needs you / late / medium risk — never errors |
| `--danger` | `#B42318` | Failed / overdue / delete |

Accent never used for status decoration. Warning never used for errors.

### 4.2 Dark tokens (from Today dark / Color usage)

Map the same semantic names to dark surfaces (`--canvas` ≈ `#0B0F14`, surfaces `#11171D` / `#1B232C`, accent stays teal family with `#2DD4BF` highlights where mockup uses them for listening). Implement via `data-theme="dark"` on `<html>` (and `prefers-color-scheme` when Appearance = System).

### 4.3 Type and layout metrics

- Font: Inter (already in app)
- Display ~30 / Title 18 / Body 14 / Small 13 / Caption 12
- Nav width **248px** (collapsed **64px** on desktop toggle; drawer on mobile)
- Header height **56px**; content padding **28×32**; section gap **18**
- Comfortable vs Compact: compact row height **36**, padding **12**, gap **16**
- Radius: cards **12**, controls **8**, pills **99**

### 4.4 Shared atoms

StatusChip vocabulary from Components (Pending, Needs you, Done, Listening, Paused, Failed, Late, …). CompactRow. Primary/secondary/danger buttons with labels Approve / Edit / Deny / Delete where those actions exist. Density toggle control. Autonomy chip + Pause + Listening/Paused pills.

## 5. Shell

### 5.1 Nav groups

- **Primary:** Today, Chat, Inbox (badge = open needs-you count only)
- **My work:** Tasks, Goals, Calendar, Mail
- **AURA:** Memory, Routines, Activity + **Agent listening / Paused** status line (from `/api/agent/control`)
- **Footer:** Connections, Settings, Help

### 5.2 Header

- Page title
- Quick-ask field copy: **“Ask or tell AURA…”** + Cmd/Ctrl+K → existing QuickAskDrawer
- Autonomy chip → popover (preset summary, link to Settings → Permissions)
- Pause / Resume (live `/api/agent/control`)
- **Bell** restored: short list — Needs you (approvals/suggestions) + Updates (recent activity); CTAs deep-link to Inbox / Activity; “Open Inbox” footer. Not a second workbench.
- Profile menu (account, preferences link, sign out)

### 5.3 Help chrome

Remove the permanent right-rail HelpPanel from every app page. Help is a first-class route; optional one-line contextual tip on complex pages only if it does not fight the mockup composition.

## 6. Screens

### Today

Greeting + one summary sentence from `/api/today`. Sections: Needs you (≤3), Now and next (+ Stop), Today’s plan, In progress goals, Since you last looked, side Getting started / connection warnings only when relevant. **Comfortable | Compact** toggle (local preference). Dark theme follows Appearance. Skeletons while loading; omit empty sections without CTA.

### Chat

Thread list (Today / Earlier) + composer + streaming. Action cards from `result_type` only (plan / approval / receipt / draft / calendar / task / …).

### Inbox

Tabs Needs you | Done; urgency ordering; suggestion source citation; approval cards.

### Tasks

Views: List | Board; filters Today / Upcoming / Overdue / All / Done. Live task APIs only.

### Goals

List + detail with progress, success criteria, plan steps, Approve/Cancel plan.

### Calendar

Today / Week / Day controls; “Find time with AURA” opens quick-ask or Chat with a fixed prompt — does not invent slots. Connect CTA when Google disconnected.

### Mail

When connected: client-side buckets **Needs reply / Waiting on / FYI / Drafts by AURA / Done** derived from list metadata + known draft/approval state; never invent messages. Untrusted banner on body/snippet. Disconnected → ConnectPrompt.

### Memory

Tabs All / Facts / People / Playbooks / **Proposed**. Proposed = pending memory proposals from agent (existing memory-proposal flow / API if present; empty honest state otherwise). Confirm before save.

### Routines

Scheduled list, enable/disable, Run now, quiet hours + daily cap fields (already on API).

### Activity

Human-first summary lines; ids in drawer; pagination when >20 rows.

### Connections

Broken/needs-attention only as warnings; healthy channels quiet.

### Settings

Profile · Agent · **Permissions** · **Appearance** (Light / Dark / System) · Data. Permissions: presets + pause + budgets as today.

### First-run wizard

Four steps: **1 Profile → 2 Model → 3 Connect → 4 Autonomy**. Model step: show current provider from `/api/status` (read-only honesty if cloud-managed). Connect: optional Google/Telegram skip. Autonomy: Ask first / Balanced / Proactive.

### Help

How AURA works loop + W1–W6 workflow sections from mockup copy (no fake live data).

## 7. Backend / API

Prefer existing contracts (`/api/today`, inbox, agent/control, google, memories, tasks, goals). Add only if a screen cannot render honestly:

- Appearance preference on owner profile (or local-only theme if migration deferred — prefer profile JSON for sync)
- Optional `GET` fields for mail bucket hints only if client-side bucketing is insufficient

No mock list endpoints.

## 8. Testing

- Unit: density helpers, mail bucketing, theme class application
- Playwright: shell (bell, autonomy, pause), Today density, dark theme toggle, Mail disconnected, Memory Proposed empty, first-run four steps smoke
- No invented facts in e2e fixtures beyond mocked API payloads

## 9. Docs

- This spec; implementation plan under `docs/superpowers/plans/`
- ADR for dark theme + appearance preference if persisted
- Update README / feature-status only if new capabilities appear

## 10. Commit order

0. Tokens + dark + atoms + density  
1. Shell: nav status, bell drawer, autonomy/profile menus, remove permanent Help rail  
2. Today density + mobile polish  
3. Chat + Inbox visual parity  
4. Tasks board + Memory Proposed  
5. Mail buckets + Calendar chrome  
6. Appearance/dark + 4-step wizard  
7. Help W1–W6 + Connections/Activity/Routines polish  
8. Tests + ADRs + status  

---

## Spec self-review

- Coverage: all product frames from the 30-frame board mapped; museum/storyboard frames explicitly out or folded into Help/atoms.  
- No TBD placeholders.  
- Types/APIs named consistently with existing AURA ports.  
- Truth/safety constraints restated.
