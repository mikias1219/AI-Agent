# AURA UX Lists / Markdown / Telegram Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Important Gmail (≤100) + upcoming Calendar with pagination, assistant Markdown in chat, dashboard-owned agent tasks visible, Telegram replies only when needed.

**Architecture:** Fix `GoogleApiClient` list queries/windows; lightweight assistant Markdown renderer (no new npm dep if possible); task ownership under `dashboard`; `telegram_reply_gate` before ChatService turn.

**Tech Stack:** FastAPI/httpx Google client, Next.js chat UI, TelegramBotRunner

**Spec:** `docs/superpowers/specs/2026-11-11-aura-ux-lists-markdown-telegram-design.md`

## Global Constraints

- Gmail: `is:important` only; window ≤100; paginate within window
- Calendar: upcoming only (`timeMin=now`); ≤100; paginate
- Assistant Markdown only; user bubbles plain
- Telegram: reply on question/request/action; silent otherwise; commands always reply; gate failure → reply (fail open)
- Keep UI simple — same pages
- Prefer no new frontend package unless necessary; skip local npm install if modules incomplete — use Prettier/ruff; pytest via `.venv`
- Do not expand OAuth scopes

## File map

| File | Role |
| --- | --- |
| `backend/.../google/clients.py` | list_gmail / list_calendar fixes |
| `backend/tests/unit/test_google_list_queries.py` | Client list tests |
| `frontend/features/chat/assistant-markdown.tsx` | Light Markdown render |
| `frontend/features/chat/message-list.tsx` | Use markdown for assistant |
| `backend/.../tools/builtins/tasks.py` + chat/telegram identity | Ensure dashboard owner |
| `backend/.../telegram_reply_gate.py` | needs_reply classifier |
| `backend/.../telegram/runner.py` | Wire gate |
| `backend/tests/unit/test_telegram_reply_gate.py` | Gate tests |
| Google page copy | Important / Upcoming labels |

---

### Task 1: Google list client fixes

**Files:** `clients.py`, `tests/unit/test_google_list_queries.py`

- [ ] **Step 1: Failing tests** — assert Gmail request includes `q` containing `is:important` and `maxResults` ≤100; Calendar request has `timeMin` ≈ now (not 1970) and `orderBy=startTime`.
- [ ] **Step 2: Implement** — Gmail: `q="is:important"`, fetch up to 100 refs (use pageToken loop if needed to fill window once, then slice by page/page_size). Calendar: `timeMin=datetime.now(UTC).strftime(...)`, max 100, paginate slice. `total` = len(window) ≤100.
- [ ] **Step 3: pytest pass** + commit `fix(google): Important Gmail and upcoming Calendar lists`

### Task 2: Assistant Markdown

**Files:** create `assistant-markdown.tsx`, modify `message-list.tsx`

- [ ] **Step 1:** Implement small renderer: paragraphs, `**bold**`, `*italic*`, `` `code` ``, `- ` / `* ` lists, bare URLs as links. Escape HTML. No new dependency.
- [ ] **Step 2:** MessageList: assistant → `<AssistantMarkdown>`, user → plain text.
- [ ] **Step 3:** Commit `feat(chat): render light Markdown in assistant bubbles`

### Task 3: Task visibility

**Files:** verify `tasks.py`, `chat_service.py`, telegram identity; FE tasks page if stale

- [ ] **Step 1:** Confirm dashboard chat + private TG create with owner `dashboard`. If any agent path uses raw `telegram:…` for tools when it should be workspace tasks, set `identity_user_id="dashboard"` consistently for private chats (already present — verify tests).
- [ ] **Step 2:** Add unit test: task_create with ctx.user_id dashboard appears in tasks.list filtered.
- [ ] **Step 3:** Commit `fix(tasks): ensure agent tasks owned by dashboard`

### Task 4: Telegram reply gate

**Files:** create `application/services/telegram_reply_gate.py`, modify `runner.py`, tests

- [ ] **Step 1: Tests** — needs_reply True for questions (`?`, “can you”, “please”, “help”, “send”, “remind”); False for “ok”, “thanks”, “lol”, single emoji; empty → False.
- [ ] **Step 2: Implement** heuristic classifier (lowercase rules; keep simple, documented).
- [ ] **Step 3: Wire runner** — after allowlist, before turn; commands unchanged; ignore audits `telegram.ignored_no_reply`.
- [ ] **Step 4: pytest + commit `feat(telegram): reply only when message needs a response`

### Task 5: Copy + verify

- [ ] Google page short copy for Important / Upcoming
- [ ] Run backend pytest subsets; ruff/format; prettier if possible
- [ ] Update spec status to Implemented; commit docs
- [ ] Merge path left to finish skill / user deploy

---

## Self-review

Spec coverage: Gmail Important≤100 ✓, Calendar upcoming ✓, Markdown ✓, Tasks ✓, Telegram B ✓, simple UI ✓. No TBD.
