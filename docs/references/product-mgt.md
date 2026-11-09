# Reference: IE Product Hub (Product-Mgt) → AURA Personal Agent Hub

**Cloned to:** `/home/mikias/Desktop/Product-Mgt`  
**Source:** https://github.com/IE-Product/Product-Mgt.git  

## Implemented in AURA (this pivot)

AURA’s Vite frontend now follows Product-Mgt’s hub IA and light chrome:

- Sidebar channel groups (Messaging / Google / Social)
- Dashboard, Board, Ideas & roadmap
- Per-channel tabs: Skills, Requests, Board, Roadmap
- Ctrl+K search, approvals bell
- Workflow statuses `draft → defined → building → live`
- Persisted hub state via `GET/PUT /api/hub/state`
- Telegram live controls; Google OAuth connect path; social scaffolds only

## Domain remap

| Product-Mgt | AURA Personal Agent Hub |
| --- | --- |
| Product / Agent | Channel agent (Telegram, Gmail, …) |
| Capability | Channel capability |
| Skill / Workflow | Hermes automation skill |
| Action / FlowStep | Tool step + approval |
| Ideas / RICE | Personal automation roadmap |

## Non-goals kept

- No Next.js runtime
- No public share links by default
- No fake social metrics
- No paid cloud LLMs
