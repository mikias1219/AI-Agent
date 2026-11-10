# AURA Agentic E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AURA act end-to-end — chat/Telegram agent tools for Google + Telegram (writes approval-gated), clear approval notifications, single header profile, runtime under chat, Telegram page as connection-not-ops.

**Architecture:** Register Google and Telegram tools on the existing `ToolRegistryImpl` + `ApprovalGatewayImpl`. Write tools use `access_kind="execute"` so they always require approval. Extend `GoogleApiClient` with send-mail and calendar write helpers (Drive stays read-only). Auto-start `TelegramWorker` when token + allowlist are configured. Frontend: strip sidebar profile, live approvals in notifications, runtime chip under composer, simplify Telegram UX.

**Tech Stack:** FastAPI, ToolRegistry, httpx Google/Telegram clients, Next.js App Router, existing `/api/approvals`.

**Spec:** `docs/superpowers/specs/2026-11-10-aura-agentic-e2e-design.md`

## Global Constraints

- New **write** tools MUST use `access_kind="execute"` (approval-gated). Do **not** change existing task tools (`prepare`) in this wave.
- Do **not** expand Google OAuth scopes; Drive remains read-only; Gmail send via existing `gmail.compose`; Calendar writes via `calendar.events`.
- Do **not** add in-app Telegram allowlist editing or pairing UI.
- Do **not** change production secrets / deploy cutover.
- Never commit tokens, OAuth secrets, or bot tokens.
- Prefer TDD for backend tools; frontend has no unit test harness — verify with `npm run lint` / `npx tsc --noEmit` and manual UI checks listed in each task.
- Follow existing builtins pattern in `application/tools/builtins/tasks.py`.

## File map

| File | Responsibility |
| --- | --- |
| `backend/.../tools/builtins/google.py` | Agent Google tools (create) |
| `backend/.../tools/builtins/telegram.py` | Agent Telegram tools (create) |
| `backend/.../integrations/google/clients.py` | Add send_gmail + calendar create/update |
| `backend/.../integrations/google/session.py` | Shared access-token provider for tools (create; extract refresh logic from app routes) |
| `backend/src/personal_agent/app/container.py` | Register new tools; wire Google/Telegram deps |
| `backend/.../presentation/web/app.py` | Lifespan auto-start Telegram; optionally use shared Google session |
| `backend/.../integrations/telegram/worker.py` | Keep start idempotent; update docstring |
| `backend/tests/unit/test_google_tools.py` | Google tool tests (create) |
| `backend/tests/unit/test_telegram_tools.py` | Telegram tool tests (create) |
| `backend/tests/unit/test_google_client_writes.py` | Client write helpers (create) |
| `frontend/components/shell/app-sidebar.tsx` | Remove profile footer |
| `frontend/features/chat/runtime-chip.tsx` | Small status chip (create) |
| `frontend/features/chat/composer.tsx` / `chat-page.tsx` | Mount runtime chip under composer |
| `frontend/components/shell/notifications-drawer.tsx` | Live approvals + decide |
| `frontend/components/shell/dashboard-layout.tsx` | Pass refresh callback / poll approvals |
| `frontend/features/connections/telegram/*` | Connection + acting UX; drop Start/Stop/Verify primary UI |
| `frontend/features/settings/permissions-section.tsx` | Fix Google preview copy |
| `frontend/features/connections/channel-grid.tsx` | Telegram copy without start/stop |

---

### Task 1: Shell — single profile + runtime chip + copy fixes

**Files:**
- Modify: `frontend/components/shell/app-sidebar.tsx`
- Create: `frontend/features/chat/runtime-chip.tsx`
- Modify: `frontend/features/chat/composer.tsx`
- Modify: `frontend/features/chat/chat-page.tsx`
- Modify: `frontend/features/settings/permissions-section.tsx`
- Modify: `frontend/features/connections/channel-grid.tsx`

**Interfaces:**
- Consumes: `getStatus()` → `StatusPayload` (`provider`, `model`, `active_runtime`)
- Produces: `RuntimeChip` under composer; sidebar with no profile block

- [ ] **Step 1: Remove sidebar profile footer**

In `app-sidebar.tsx`, delete the footer block that renders `Avatar` + name + email (the `border-t` section at the bottom of the aside). Keep nav only. If `user` becomes unused, remove it from `AppSidebar` props and update `dashboard-layout.tsx` call site.

- [ ] **Step 2: Add `RuntimeChip`**

Create `frontend/features/chat/runtime-chip.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { getStatus } from "@/lib/api/status";

export function RuntimeChip() {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getStatus()
      .then((s) => {
        if (!cancelled) setLabel(`${s.provider} · ${s.model} · ${s.active_runtime}`);
      })
      .catch(() => {
        if (!cancelled) setLabel(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!label) return null;
  return (
    <p className="text-xs text-[var(--muted)]" aria-label="Agent runtime">
      {label}
    </p>
  );
}
```

- [ ] **Step 3: Mount chip under composer**

In `composer.tsx`, render children or accept an optional `footer` slot — simplest: in `chat-page.tsx`, place `<RuntimeChip />` immediately above or below `<Composer ... />` inside the composer column (under the input area). Prefer **below** the composer form so it sits under the send row.

- [ ] **Step 4: Fix stale Google “Preview” copy**

Update `permissions-section.tsx` honesty bullet from claiming Google is preview-only to: Google uses live APIs when connected; LinkedIn/Facebook remain previews.

In `channel-grid.tsx` `telegramCard`, change description text that says “Start or stop the bot…” to something like “Token set. Agent uses Telegram when allowlisted chats are configured.”

- [ ] **Step 5: Verify frontend**

Run:

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: no errors related to these files.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/shell/app-sidebar.tsx frontend/components/shell/dashboard-layout.tsx \
  frontend/features/chat/runtime-chip.tsx frontend/features/chat/composer.tsx \
  frontend/features/chat/chat-page.tsx frontend/features/settings/permissions-section.tsx \
  frontend/features/connections/channel-grid.tsx
git commit -m "$(cat <<'EOF'
feat(ui): single header profile and chat runtime chip

Remove sidebar profile, show live provider/model under chat, and fix
stale Google/Telegram ops copy.
EOF
)"
```

---

### Task 2: Live approval notifications

**Files:**
- Modify: `frontend/components/shell/notifications-drawer.tsx`
- Modify: `frontend/components/shell/dashboard-layout.tsx`
- Optionally stop using: `frontend/lib/mocks/notifications.ts` from the drawer (mocks may remain for other demos)

**Interfaces:**
- Consumes: `listApprovals()`, `decideApproval(id, "approve"|"reject")` from `@/lib/api/tasks`
- Produces: Drawer lists real pending approvals with Approve/Reject; badge count refreshes after decide

- [ ] **Step 1: Rewrite drawer to load live approvals**

Replace mock `notificationsWithApprovals` usage. When `open` is true, call `listApprovals()` and show each pending item with `tool_name`, short JSON/summary of `arguments`, origin, and Approve/Reject buttons (reuse patterns from `task-approve-modal.tsx`). Keep EmptyState when none.

Sketch:

```tsx
const [items, setItems] = useState<Approval[]>([]);
const [busyId, setBusyId] = useState<string | null>(null);

useEffect(() => {
  if (!open) return;
  let cancelled = false;
  listApprovals()
    .then((rows) => {
      if (!cancelled) setItems(rows.filter((r) => r.actionable));
    })
    .catch(() => {
      if (!cancelled) setItems([]);
    });
  return () => {
    cancelled = true;
  };
}, [open, refreshKey]);

async function decide(id: string, decision: ApprovalDecision) {
  setBusyId(id);
  try {
    await decideApproval(id, decision);
    setItems((prev) => prev.filter((a) => a.id !== id));
    onApprovalChanged?.();
  } finally {
    setBusyId(null);
  }
}
```

Add optional `onApprovalChanged?: () => void` prop so the layout can refresh the badge count.

- [ ] **Step 2: Wire layout polling / refresh**

In `dashboard-layout.tsx`:
- Extract a `refreshApprovals()` that sets count from `listApprovals()` (prefer `listApprovals` over raw `api`).
- Pass `onApprovalChanged={refreshApprovals}` into the drawer.
- Optionally re-poll every 15–30s while mounted so chat-triggered approvals update the badge without reload.

- [ ] **Step 3: Verify**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Manual: open notifications with a pending approval (after Task 4/5 exist) — for now, empty state is fine.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/shell/notifications-drawer.tsx frontend/components/shell/dashboard-layout.tsx
git commit -m "$(cat <<'EOF'
feat(ui): wire notifications drawer to live approvals

Approve or reject pending tool calls from the header drawer and refresh
the badge count.
EOF
)"
```

---

### Task 3: Google client write helpers + session token provider

**Files:**
- Create: `backend/src/personal_agent/infrastructure/integrations/google/session.py`
- Modify: `backend/src/personal_agent/infrastructure/integrations/google/clients.py`
- Create: `backend/tests/unit/test_google_client_writes.py`
- Modify: `backend/src/personal_agent/presentation/web/app.py` (optional: call shared session; keep behavior identical)

**Interfaces:**
- Produces:
  - `GoogleTokenProvider(store, settings) -> Callable[[], str]` raising `GoogleNotConnectedError` / `GoogleApiError` (not HTTPException)
  - `GoogleApiClient.send_gmail(to: str, subject: str, body: str) -> dict`
  - `GoogleApiClient.create_calendar_event(...)` / `update_calendar_event(...)`

- [ ] **Step 1: Write failing client tests**

```python
# backend/tests/unit/test_google_client_writes.py
import base64
import json
import httpx
import pytest
from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient, GoogleApiError

def test_send_gmail_posts_raw_message():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"id": "m1", "labelIds": ["SENT"]})

    transport = httpx.MockTransport(handler)
    client = GoogleApiClient(
        access_token_provider=lambda: "tok",
        http_client=httpx.Client(transport=transport),
    )
    result = client.send_gmail(to="a@b.com", subject="Hi", body="Hello")
    assert result["id"] == "m1"
    assert "gmail.googleapis.com" in seen["url"] and seen["url"].endswith("/messages/send")
    raw = base64.urlsafe_b64decode(seen["body"]["raw"] + "==")
    assert b"To: a@b.com" in raw
    assert b"Subject: Hi" in raw

def test_create_calendar_event_posts_primary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "calendars/primary/events" in str(request.url)
        return httpx.Response(200, json={"id": "e1", "summary": "Sync"})

    client = GoogleApiClient(
        access_token_provider=lambda: "tok",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    out = client.create_calendar_event(
        title="Sync",
        starts_at="2026-11-11T10:00:00Z",
        ends_at="2026-11-11T11:00:00Z",
        location="",
    )
    assert out["id"] == "e1"
```

- [ ] **Step 2: Run tests — expect fail**

```bash
cd backend && python -m pytest tests/unit/test_google_client_writes.py -v
```

Expected: FAIL (methods missing).

- [ ] **Step 3: Implement client methods**

Add `_post`/`_patch` similar to `_get`. Implement:

- `send_gmail`: build RFC 2822 message, base64url encode (no padding), POST `https://gmail.googleapis.com/gmail/v1/users/me/messages/send` with `{"raw": ...}`.
- `create_calendar_event`: POST `.../calendars/primary/events` with `summary`, `location`, `start`/`end` as `dateTime`+`timeZone` UTC or pass through ISO.
- `update_calendar_event`: PATCH `.../calendars/primary/events/{id}` with provided fields.

Raise `GoogleApiError` on HTTP >= 400.

- [ ] **Step 4: Implement `session.py` token provider**

```python
# backend/src/personal_agent/infrastructure/integrations/google/session.py
class GoogleNotConnectedError(RuntimeError):
    pass

def make_access_token_provider(*, store, settings) -> Callable[[], str]:
    def provider() -> str:
        tokens = store.load_tokens()
        access = tokens.get("access_token") or ""
        refresh = tokens.get("refresh_token") or ""
        if not access and not refresh:
            raise GoogleNotConnectedError(
                "Google is not connected. Connect Google under Connections."
            )
        # refresh when possible using GoogleOAuthClient + settings; save back to store
        ...
        if not access:
            raise GoogleNotConnectedError("Google access token missing. Reconnect Google.")
        return access

    return provider
```

Mirror refresh logic from `app.py` `_google_access_token` but raise `GoogleNotConnectedError` instead of `HTTPException`. Optionally refactor `app.py` to wrap this provider and map errors to HTTP — nice-to-have, not required if tests cover session separately.

- [ ] **Step 5: Tests pass**

```bash
cd backend && python -m pytest tests/unit/test_google_client_writes.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/personal_agent/infrastructure/integrations/google/clients.py \
  backend/src/personal_agent/infrastructure/integrations/google/session.py \
  backend/tests/unit/test_google_client_writes.py \
  backend/src/personal_agent/presentation/web/app.py
git commit -m "$(cat <<'EOF'
feat(google): add send/calendar write client helpers

Support agent write tools with a shared token provider that raises
domain errors when Google is disconnected.
EOF
)"
```

---

### Task 4: Google agent tools + registry wiring

**Files:**
- Create: `backend/src/personal_agent/application/tools/builtins/google.py`
- Modify: `backend/src/personal_agent/app/container.py`
- Create: `backend/tests/unit/test_google_tools.py`

**Interfaces:**
- Consumes: `GoogleConnectionStore`, `make_access_token_provider`, `GoogleApiClient`
- Produces tools:
  - `google_gmail_list` (`read`)
  - `google_calendar_list` (`read`)
  - `google_drive_list` (`read`)
  - `google_gmail_send` (`execute`) — args: `to`, `subject`, `body`
  - `google_calendar_create` (`execute`) — args: `title`, `starts_at`, `ends_at`, optional `location`
  - `google_calendar_update` (`execute`) — args: `event_id`, optional fields
- Factory: `def google_tools(*, client: GoogleApiClient) -> list[ToolSpec]`

- [ ] **Step 1: Failing tool tests**

```python
# backend/tests/unit/test_google_tools.py
import json
import pytest
from personal_agent.application.tools.builtins.google import google_tools
from personal_agent.domain.exceptions import PermissionDeniedError
from personal_agent.domain.models import ToolCall
from personal_agent.infrastructure.integrations.google.session import GoogleNotConnectedError

class FakeClient:
    def __init__(self):
        self.sent = None
    def list_gmail(self, *, page, page_size):
        return {"items": [{"id": "1", "subject": "Hi"}], "page": page, "page_size": page_size, "total": 1}
    def send_gmail(self, *, to, subject, body):
        self.sent = (to, subject, body)
        return {"id": "m1"}

def test_gmail_list_is_read_and_returns_json(tool_registry, ctx):
    client = FakeClient()
    tool_registry.register_all(google_tools(client=client))
    result = tool_registry.execute(ToolCall(id="1", name="google_gmail_list", arguments={"page": 1, "page_size": 5}), ctx)
    assert result.ok
    assert json.loads(result.output)["items"][0]["subject"] == "Hi"

def test_gmail_send_requires_approval(tool_registry, ctx):
    # default fixture: no notifier → deferred → PermissionDeniedError
    tool_registry.register_all(google_tools(client=FakeClient()))
    with pytest.raises(PermissionDeniedError):
        tool_registry.execute(
            ToolCall(id="2", name="google_gmail_send", arguments={"to": "a@b.com", "subject": "S", "body": "B"}),
            ctx,
        )

def test_gmail_send_runs_when_approved(session_factory, ctx, policy, audit_log):
    from personal_agent.application.security.approvals import ApprovalGatewayImpl
    from personal_agent.application.tools.registry import ToolRegistryImpl
    from personal_agent.infrastructure.persistence.repositories import ApprovalRepositoryImpl

    client = FakeClient()
    registry = ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory),
            audit=audit_log,
            notifier=lambda _p, _d: "approved",
        ),
        audit=audit_log,
    )
    registry.register_all(google_tools(client=client))
    result = registry.execute(
        ToolCall(id="3", name="google_gmail_send", arguments={"to": "a@b.com", "subject": "S", "body": "B"}),
        ctx,
    )
    assert result.ok and client.sent == ("a@b.com", "S", "B")
```

Also add a test where client raises `GoogleNotConnectedError` and the tool result `ok is False` with that message (handler exception → failed ToolResult).

- [ ] **Step 2: Run — expect fail**

```bash
cd backend && python -m pytest tests/unit/test_google_tools.py -v
```

- [ ] **Step 3: Implement `google.py`**

Follow `task_tools` style: build `ToolSpec` list. Reads call list_* with page defaults. Writes call send/create/update. No Drive write tools.

- [ ] **Step 4: Wire in `container.py`**

After Google store exists and before/after `task_tools`:

```python
from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient
from personal_agent.infrastructure.integrations.google.session import make_access_token_provider
from personal_agent.application.tools.builtins.google import google_tools

google_store = GoogleConnectionStore(...)  # already created as today
token_provider = make_access_token_provider(store=google_store, settings=settings)
google_client = GoogleApiClient(access_token_provider=token_provider)
registry.register_all(google_tools(client=google_client))
```

Ensure store is constructed before registration (reorder if needed — today store is created at return time; construct earlier like today’`s pattern or register just before `return`).

- [ ] **Step 5: Tests pass**

```bash
cd backend && python -m pytest tests/unit/test_google_tools.py tests/security/test_approval_flow.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/personal_agent/application/tools/builtins/google.py \
  backend/src/personal_agent/app/container.py \
  backend/tests/unit/test_google_tools.py
git commit -m "$(cat <<'EOF'
feat(agent): register Google read/write tools

List Gmail/Calendar/Drive without approval; gate send and calendar
writes behind execute approvals.
EOF
)"
```

---

### Task 5: Telegram agent tools

**Files:**
- Create: `backend/src/personal_agent/application/tools/builtins/telegram.py`
- Modify: `backend/src/personal_agent/app/container.py`
- Create: `backend/tests/unit/test_telegram_tools.py`

**Interfaces:**
- Consumes: `TelegramBotClient | None`, `allowed_chat_ids: frozenset[int]`, audit/activity source
- Produces:
  - `telegram_list_activity` (`read`) — recent audit events (same filter as `/api/telegram/activity`) OR return allowlisted chat ids + last N activity dicts via injected callable
  - `telegram_send_message` (`execute`) — args: `chat_id` (int), `text` (str); hard-fail if client missing, allowlist empty, or `chat_id` not allowlisted
- Factory: `telegram_tools(*, client, allowed_chat_ids, list_activity: Callable[[], list[dict]]) -> list[ToolSpec]`

- [ ] **Step 1: Failing tests**

```python
# backend/tests/unit/test_telegram_tools.py
import pytest
from personal_agent.application.tools.builtins.telegram import telegram_tools
from personal_agent.domain.exceptions import PermissionDeniedError
from personal_agent.domain.models import ToolCall

class FakeTg:
    def __init__(self):
        self.sent = []
    def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))

def test_send_blocked_when_not_allowlisted(session_factory, ctx, policy, audit_log):
    from personal_agent.application.security.approvals import ApprovalGatewayImpl
    from personal_agent.application.tools.registry import ToolRegistryImpl
    from personal_agent.infrastructure.persistence.repositories import ApprovalRepositoryImpl

    tg = FakeTg()
    registry = ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory),
            audit=audit_log,
            notifier=lambda _p, _d: "approved",
        ),
        audit=audit_log,
    )
    registry.register_all(
        telegram_tools(client=tg, allowed_chat_ids=frozenset({42}), list_activity=lambda: [])
    )
    result = registry.execute(
        ToolCall(id="1", name="telegram_send_message", arguments={"chat_id": 99, "text": "hi"}),
        ctx,
    )
    assert result.ok is False
    assert tg.sent == []

def test_send_requires_approval(tool_registry, ctx):
    tool_registry.register_all(
        telegram_tools(client=FakeTg(), allowed_chat_ids=frozenset({1}), list_activity=lambda: [])
    )
    with pytest.raises(PermissionDeniedError):
        tool_registry.execute(
            ToolCall(id="2", name="telegram_send_message", arguments={"chat_id": 1, "text": "hi"}),
            ctx,
        )

def test_send_ok_when_approved(session_factory, ctx, policy, audit_log):
    # same registry as above with approving notifier
    ...
    assert tg.sent == [(1, "hi")]
```

- [ ] **Step 2: Implement `telegram.py`**

On send: if `client is None` → fail “Telegram is not configured.”; if allowlist empty → fail “Telegram allowlist is empty.”; if chat_id not in allowlist → fail “Chat is not allowlisted.”; else `client.send_message`.

For list activity: return JSON of `list_activity()` capped to ~20 items.

- [ ] **Step 3: Wire container**

```python
from personal_agent.application.tools.builtins.telegram import telegram_tools
from personal_agent.infrastructure.integrations.telegram.runner import build_allowed_chats

allowed = build_allowed_chats(settings.telegram_allowed_chat_ids)

def _telegram_activity():
    # reuse audit filter used by GET /api/telegram/activity — extract helper if needed
    return approvals_or_audit_list(...)

registry.register_all(
    telegram_tools(
        client=telegram_client,
        allowed_chat_ids=allowed,
        list_activity=_telegram_activity,
    )
)
```

If extracting the activity query is awkward, inline the same event-name filter the route uses (copy from `app.py` telegram activity handler).

- [ ] **Step 4: Tests pass**

```bash
cd backend && python -m pytest tests/unit/test_telegram_tools.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/personal_agent/application/tools/builtins/telegram.py \
  backend/src/personal_agent/app/container.py \
  backend/tests/unit/test_telegram_tools.py \
  backend/src/personal_agent/presentation/web/app.py
git commit -m "$(cat <<'EOF'
feat(agent): register Telegram activity and send tools

Allowlisted sends require approval; non-allowlisted chats hard-fail.
EOF
)"
```

---

### Task 6: Telegram auto-start + connection UX

**Files:**
- Modify: `backend/src/personal_agent/presentation/web/app.py` (lifespan startup)
- Modify: `backend/src/personal_agent/infrastructure/integrations/telegram/worker.py` (docstring)
- Modify: `frontend/features/connections/telegram/telegram-page.tsx`
- Modify: `frontend/features/connections/telegram/telegram-status-panel.tsx`
- Modify: `frontend/features/connections/telegram/use-telegram.ts`

**Interfaces:**
- Produces: worker starts when `telegram_worker` exists **and** allowlist non-empty; UI shows Connected / Acting as you + activity; no primary Start/Stop/Verify

- [ ] **Step 1: Auto-start in lifespan**

```python
@asynccontextmanager
async def lifespan(_app):
    worker = container.telegram_worker
    allowed = build_allowed_chats(container.settings.telegram_allowed_chat_ids)
    if worker and allowed:
        try:
            await asyncio.to_thread(worker.start)
        except Exception:
            logger.exception("Telegram auto-start failed")
    yield
    if worker:
        await asyncio.to_thread(worker.close)
```

Keep POST start/stop/verify endpoints for debug but they are not product UI.

Update worker module docstring: dashboard may auto-start when configured.

- [ ] **Step 2: Simplify Telegram frontend**

- Page subtitle: “Connected to your Telegram. The agent acts in allowlisted chats.”
- Status panel: show configured / allowlist present / runtime phase (Listening/Acting) / last seen — **remove Verify / Start / Stop buttons** and “First reply” procedure block.
- `use-telegram.ts`: stop exporting verify/start/stop for the page (may leave API helpers unused or keep for rare debug — do not call from page).
- Keep Refresh + activity list.

Connected semantics for copy:
- **Connected:** `status.telegram.configured && allowed_chat_ids.length > 0`
- **Acting as you:** `managed && runtime` in listening/answering (use existing runtime labels from `format.ts`)

- [ ] **Step 3: Frontend check**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

- [ ] **Step 4: Backend smoke for auto-start (unit if easy)**

If lifespan is hard to unit-test, add a small helper `should_autostart_telegram(worker, allowed) -> bool` and test that.

- [ ] **Step 5: Commit**

```bash
git add backend/src/personal_agent/presentation/web/app.py \
  backend/src/personal_agent/infrastructure/integrations/telegram/worker.py \
  frontend/features/connections/telegram/
git commit -m "$(cat <<'EOF'
feat(telegram): auto-start worker and connection-first UI

Drop start/stop/verify as the product path; show connected/acting
status and recent activity instead.
EOF
)"
```

---

### Task 7: End-to-end verification + spec status

**Files:**
- Modify: `docs/superpowers/specs/2026-11-10-aura-agentic-e2e-design.md` (Status → Implemented / ready for review)
- Optionally: short note in `docs/deploy.md` only if Telegram auto-start behavior needs operator clarity (no secret changes)

- [ ] **Step 1: Run backend suite subset**

```bash
cd backend && python -m pytest tests/unit/test_google_client_writes.py tests/unit/test_google_tools.py tests/unit/test_telegram_tools.py tests/security/test_approval_flow.py -v
```

Expected: all PASS.

- [ ] **Step 2: Run frontend checks**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

- [ ] **Step 3: Manual smoke (local or production with real creds)**

1. Chat: “list my recent gmail” → tool runs when Google connected.
2. Chat: “email X saying Y” → pending approval in header → Approve → sent.
3. Chat: “send telegram to \<allowlisted id\> …” → approval → sent.
4. Telegram page: no Start/Stop/Verify; shows connected/acting + activity.
5. Sidebar: no profile; header profile works; runtime chip under chat.

- [ ] **Step 4: Mark spec status and commit**

Update design doc status line to `Approved — implementation complete` (or `Implemented`) and commit docs if changed.

```bash
git add docs/superpowers/specs/2026-11-10-aura-agentic-e2e-design.md docs/deploy.md
git commit -m "$(cat <<'EOF'
docs: mark agentic E2E spec implemented

Record verification status after Google/Telegram agent tools and UI
cleanup landed.
EOF
)"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
| --- | --- |
| Google full-act within scopes; Drive read-only | Tasks 3–4 |
| Write-only approvals (`execute`) | Tasks 4–5 |
| Clear approval/notification UI | Task 2 |
| Profile header only | Task 1 |
| Runtime under chat | Task 1 |
| Telegram agent tools + no ops UI + auto-start | Tasks 5–6 |
| Overview/capabilities Preview mismatch | Task 1 (permissions + channel-grid) |
| Out of scope: allowlist UI, scope expansion, Approach 2/3 | Not planned |

No TBD placeholders. Tool names consistent across tasks (`google_gmail_send`, `telegram_send_message`). Task tools left unchanged (`prepare`) despite architecture table listing them as approval writes — matches Global Constraints / YAGNI.
