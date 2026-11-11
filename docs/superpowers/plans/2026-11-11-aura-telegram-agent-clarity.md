# Telegram Agent Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/connections/telegram` an always-on agent guide (how it helps + how to use + one honest Listening/Starting/Needs setup/Error status), and align Overview/health/channel cards to the same vocabulary.

**Architecture:** One pure FE mapper (`resolveTelegramAgentState`) shared by Telegram status panel, Overview tiles, HealthStrip, and Connections channel card. Page adds How it helps / How to use sections. Backend only if allowlisted workers stay Stopped despite lifespan auto-start (heal foreign/stale skip or ensure start).

**Tech Stack:** Next.js App Router FE (TypeScript), existing Telegram status/activity APIs, FastAPI lifespan auto-start, pytest for BE, `node --test --experimental-strip-types` for FE mapper (Node ≥22.12, no new npm deps).

## Global Constraints

- Runtime: always listening (lifespan auto-start); **no** Start/Stop/Verify UI
- Status vocabulary only: **Listening** / **Starting** / **Needs setup** / **Error**
- Reply-gate policy unchanged (questions/requests reply; ok/thanks quiet)
- Spec: `docs/superpowers/specs/2026-11-11-aura-telegram-agent-clarity-design.md`
- Never show “Connected” together with “Stopped”
- Never show Overview “finish setup” when allowlisted
- Do not add LinkedIn/Facebook, keyword admin, or Chat↔Telegram sync UI

## File map

| File | Responsibility |
| --- | --- |
| `frontend/features/connections/telegram/agent-state.ts` | Pure status → user state + labels/hints/copy helpers |
| `frontend/features/connections/telegram/agent-state.test.ts` | Mapper table tests (`node --test`) |
| `frontend/features/connections/telegram/telegram-status-panel.tsx` | One status + hint using mapper |
| `frontend/features/connections/telegram/telegram-page.tsx` | Header, How it helps, How to use, activity empty copy |
| `frontend/features/overview/overview-page.tsx` | Telegram tile uses mapper |
| `frontend/features/overview/health-strip.tsx` | Telegram chip uses mapper |
| `frontend/features/connections/channel-grid.tsx` | Telegram card uses mapper |
| `frontend/features/connections/format.ts` | Prefer preview over raw chat id in activity detail |
| `backend/.../presentation/web/app.py` | Only if auto-start/foreign-runtime bug confirmed |
| `backend/tests/unit/test_telegram_autostart.py` | Extend if BE touched |

---

### Task 1: Shared Telegram agent state mapper

**Files:**
- Create: `frontend/features/connections/telegram/agent-state.ts`
- Create: `frontend/features/connections/telegram/agent-state.test.ts`
- Test: run with Node test runner

**Interfaces:**
- Consumes: `TelegramStatusPayload` shape (`configured`, `allowed_chat_ids`, `managed`, `runtime`, `username`, `error_type`, `last_seen`)
- Produces:
  - `export type TelegramAgentUiState = "listening" | "starting" | "needs_setup" | "error"`
  - `export function resolveTelegramAgentState(status: Pick<TelegramStatusPayload, "configured" | "allowed_chat_ids" | "managed" | "runtime">): TelegramAgentUiState`
  - `export function telegramAgentStatusLabel(state: TelegramAgentUiState): string` → `Listening` | `Starting` | `Needs setup` | `Error`
  - `export function telegramAgentStatusHint(state: TelegramAgentUiState, status: TelegramStatusPayload): string`
  - `export function telegramOverviewCopy(state: TelegramAgentUiState): { value: string; detail: string }`
  - `export function telegramHealthChip(state: TelegramAgentUiState): { statusLabel: string; tone: "success" | "accent" | "warning" | "neutral" }`
  - `export function telegramChannelCardCopy(state: TelegramAgentUiState): { badge: string; tone: "success" | "accent" | "warning" | "neutral"; description: string }`

- [ ] **Step 1: Write the failing test**

Create `frontend/features/connections/telegram/agent-state.test.ts`:

```ts
import assert from "node:assert/strict";
import test from "node:test";
import {
  resolveTelegramAgentState,
  telegramAgentStatusLabel,
  telegramOverviewCopy,
} from "./agent-state.ts";

function base(over: Record<string, unknown> = {}) {
  return {
    configured: true,
    allowed_chat_ids: [1],
    managed: false,
    runtime: "stopped",
    ...over,
  };
}

test("needs_setup when not configured", () => {
  assert.equal(
    resolveTelegramAgentState(base({ configured: false, allowed_chat_ids: [] })),
    "needs_setup",
  );
});

test("needs_setup when allowlist empty", () => {
  assert.equal(resolveTelegramAgentState(base({ allowed_chat_ids: [] })), "needs_setup");
});

test("error when runtime is error", () => {
  assert.equal(resolveTelegramAgentState(base({ runtime: "error" })), "error");
});

test("listening for polling/responding/running", () => {
  for (const runtime of ["polling", "responding", "running"]) {
    assert.equal(resolveTelegramAgentState(base({ runtime, managed: true })), "listening");
  }
});

test("listening when managed even if runtime is starting", () => {
  assert.equal(resolveTelegramAgentState(base({ managed: true, runtime: "starting" })), "listening");
});

test("starting when allowlisted but not yet listening", () => {
  assert.equal(resolveTelegramAgentState(base({ runtime: "stopped", managed: false })), "starting");
  assert.equal(resolveTelegramAgentState(base({ runtime: "unknown", managed: false })), "starting");
  assert.equal(resolveTelegramAgentState(base({ runtime: "stale", managed: false })), "starting");
  assert.equal(resolveTelegramAgentState(base({ runtime: "starting", managed: false })), "starting");
});

test("labels and overview copy match vocabulary", () => {
  assert.equal(telegramAgentStatusLabel("listening"), "Listening");
  assert.equal(telegramOverviewCopy("needs_setup").value, "Needs setup");
  assert.equal(telegramOverviewCopy("listening").detail, "Agent replies in Telegram");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && node --experimental-strip-types --test features/connections/telegram/agent-state.test.ts
```

Expected: FAIL (module not found or export missing).

- [ ] **Step 3: Write minimal implementation**

Create `frontend/features/connections/telegram/agent-state.ts`:

```ts
import type { TelegramStatusPayload } from "@/lib/api/types";
import type { BadgeTone } from "@/components/ui/badge";

export type TelegramAgentUiState = "listening" | "starting" | "needs_setup" | "error";

type StatusCore = Pick<
  TelegramStatusPayload,
  "configured" | "allowed_chat_ids" | "managed" | "runtime"
>;

const LISTENING_RUNTIMES = new Set(["polling", "responding", "running"]);

export function resolveTelegramAgentState(status: StatusCore): TelegramAgentUiState {
  if (!status.configured || status.allowed_chat_ids.length === 0) return "needs_setup";
  if (status.runtime === "error") return "error";
  if (LISTENING_RUNTIMES.has(status.runtime) || status.managed) return "listening";
  return "starting";
}

export function telegramAgentStatusLabel(state: TelegramAgentUiState): string {
  switch (state) {
    case "listening":
      return "Listening";
    case "starting":
      return "Starting";
    case "needs_setup":
      return "Needs setup";
    case "error":
      return "Error";
  }
}

export function telegramAgentStatusHint(
  state: TelegramAgentUiState,
  status: TelegramStatusPayload,
): string {
  switch (state) {
    case "listening":
      return "Agent is listening in your allowlisted chats.";
    case "starting":
      return "Starting your Telegram agent…";
    case "needs_setup":
      if (!status.configured) {
        return "Add TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_CHAT_IDS on the server, then restart.";
      }
      return "Add allowlisted chat IDs on the server so the agent can reply.";
    case "error":
      return status.error_type
        ? `Something went wrong (${status.error_type}). Check the bot token and try again later.`
        : "Something went wrong. Check the bot token and try again later.";
  }
}

export function telegramOverviewCopy(state: TelegramAgentUiState): {
  value: string;
  detail: string;
} {
  switch (state) {
    case "listening":
      return { value: "Listening", detail: "Agent replies in Telegram" };
    case "starting":
      return { value: "Starting", detail: "Starting your Telegram agent" };
    case "needs_setup":
      return { value: "Needs setup", detail: "Open Telegram page" };
    case "error":
      return { value: "Error", detail: "See Telegram page" };
  }
}

export function telegramHealthChip(state: TelegramAgentUiState): {
  statusLabel: string;
  tone: BadgeTone;
} {
  switch (state) {
    case "listening":
      return { statusLabel: "Listening", tone: "success" };
    case "starting":
      return { statusLabel: "Starting", tone: "accent" };
    case "needs_setup":
      return { statusLabel: "Needs setup", tone: "neutral" };
    case "error":
      return { statusLabel: "Error", tone: "warning" };
  }
}

export function telegramChannelCardCopy(state: TelegramAgentUiState): {
  badge: string;
  tone: BadgeTone;
  description: string;
} {
  switch (state) {
    case "listening":
      return {
        badge: "Listening",
        tone: "success",
        description: "Your always-on agent replies in allowlisted Telegram chats.",
      };
    case "starting":
      return {
        badge: "Starting",
        tone: "accent",
        description: "Starting your Telegram agent…",
      };
    case "needs_setup":
      return {
        badge: "Needs setup",
        tone: "neutral",
        description: "Open Telegram for setup steps.",
      };
    case "error":
      return {
        badge: "Error",
        tone: "warning",
        description: "Open Telegram to see what went wrong.",
      };
  }
}
```

Mapping rules (must match tests):

1. `!configured` OR empty allowlist → `needs_setup`
2. Else `runtime === "error"` → `error`
3. Else `polling|responding|running` OR `managed` → `listening`
4. Else → `starting` (includes stopped/unknown/stale/starting while not managed)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && node --experimental-strip-types --test features/connections/telegram/agent-state.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/features/connections/telegram/agent-state.ts frontend/features/connections/telegram/agent-state.test.ts
git commit -m "$(cat <<'EOF'
feat(telegram): shared agent status vocabulary mapper

EOF
)"
```

---

### Task 2: Telegram status panel uses mapper only

**Files:**
- Modify: `frontend/features/connections/telegram/telegram-status-panel.tsx`
- Test: re-run mapper tests (no UI runner); manual spot-check after Task 3

**Interfaces:**
- Consumes: `resolveTelegramAgentState`, `telegramAgentStatusLabel`, `telegramAgentStatusHint` from Task 1
- Produces: status panel with one label + one hint; no “Connected · waiting”; no `Status: ${runtimeLabel(...)}` line

- [ ] **Step 1: Replace panel body**

Rewrite `TelegramStatusPanel` to:

```tsx
"use client";

import { Radio } from "lucide-react";
import type { TelegramStatusPayload } from "@/lib/api/types";
import {
  resolveTelegramAgentState,
  telegramAgentStatusHint,
  telegramAgentStatusLabel,
} from "./agent-state";

export type TelegramStatusPanelProps = {
  status: TelegramStatusPayload;
};

export function TelegramStatusPanel({ status }: TelegramStatusPanelProps) {
  const state = resolveTelegramAgentState(status);
  const title = status.username ? `@${status.username}` : "Telegram";
  const listening = state === "listening";

  return (
    <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-5 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Status</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--ink)]">{title}</h2>
          <p className="mt-1 text-sm font-medium text-[var(--ink)]" role="status">
            {telegramAgentStatusLabel(state)}
          </p>
          <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
            {telegramAgentStatusHint(state, status)}
          </p>
        </div>
        <Radio
          className={`mt-1 h-5 w-5 shrink-0 ${
            listening ? "text-[var(--success)]" : "text-[var(--muted)]"
          }`}
          aria-hidden
        />
      </div>
      {status.configured && status.allowed_chat_ids.length > 0 ? (
        <p className="mt-4 text-xs text-[var(--muted)]">
          {status.allowed_chat_ids.length} allowlisted chat
          {status.allowed_chat_ids.length === 1 ? "" : "s"}
        </p>
      ) : null}
    </section>
  );
}
```

Remove local `ACTING_RUNTIMES`, `isConnected`, `isActingAsYou`, and any `runtimeLabel` usage from this file.

- [ ] **Step 2: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors from this file.

- [ ] **Step 3: Commit**

```bash
git add frontend/features/connections/telegram/telegram-status-panel.tsx
git commit -m "$(cat <<'EOF'
feat(telegram): single Listening/Starting/Needs setup/Error status

EOF
)"
```

---

### Task 3: How it helps + How to use on Telegram page

**Files:**
- Modify: `frontend/features/connections/telegram/telegram-page.tsx`
- Modify: `frontend/features/connections/format.ts` (`telegramEventDetail`)

**Interfaces:**
- Consumes: `status.username` for `https://t.me/{username}`
- Produces: guide sections + clearer empty/activity detail

- [ ] **Step 1: Update header + guide sections**

In `telegram-page.tsx`:

1. Change subtitle to:  
   `Your always-on agent on Telegram — ask here, get help without opening the dashboard.`
2. After `{status ? <TelegramStatusPanel status={status} /> : null}`, when `status` is non-null, render two sections:

**How it helps you** (ul):

- Answers questions in Telegram the same way as Chat
- Can check Important email and upcoming calendar when Google is connected
- Can create tasks; write actions still need your approval in the dashboard
- Stays quiet on casual “ok / thanks”; replies when you ask for something

**How to use** (ol):

1. Open Telegram and message the bot — if `status.username`, render link  
   `href={`https://t.me/${status.username}`}` with text `@${status.username}`; else text “your configured bot”
2. Ask a real request (examples below)
3. Return here to see Agent replied / Skipped under Recent activity

Under How to use, static example list (not buttons that send):

- What’s on my calendar today?
- Any important email I should see?
- Create a task to follow up on CI

3. Empty activity description:  
   `Ask a question in Telegram first — then replies and skips show up here.`

Keep Refresh, pagination, and activity list structure.

- [ ] **Step 2: Prefer preview in activity detail**

In `format.ts`, change `telegramEventDetail` so when `preview` is present, **do not** append `Chat ${chat_id}` (keep username / error_type as today):

```ts
export function telegramEventDetail(details: Record<string, unknown>): string {
  const parts: string[] = [];
  const preview =
    typeof details.preview === "string" && details.preview.trim()
      ? details.preview.trim()
      : "";
  if (preview) {
    parts.push(`"${preview}"`);
  } else if (details.chat_id !== undefined && details.chat_id !== null) {
    parts.push(`Chat ${String(details.chat_id)}`);
  }
  if (typeof details.username === "string" && details.username) {
    parts.push(`@${details.username}`);
  }
  if (typeof details.error_type === "string" && details.error_type) {
    parts.push(details.error_type);
  }
  return parts.join(" · ");
}
```

- [ ] **Step 3: Typecheck + format**

```bash
cd frontend && npx tsc --noEmit && npm run format
```

- [ ] **Step 4: Commit**

```bash
git add frontend/features/connections/telegram/telegram-page.tsx frontend/features/connections/format.ts
git commit -m "$(cat <<'EOF'
feat(telegram): how it helps and how to use guide

EOF
)"
```

---

### Task 4: Overview, HealthStrip, and channel grid share vocabulary

**Files:**
- Modify: `frontend/features/overview/overview-page.tsx` (Telegram tile block ~lines 112–129)
- Modify: `frontend/features/overview/health-strip.tsx` (`telegramChip`)
- Modify: `frontend/features/connections/channel-grid.tsx` (`telegramCard`)

**Interfaces:**
- Consumes: `resolveTelegramAgentState`, `telegramOverviewCopy`, `telegramHealthChip`, `telegramChannelCardCopy`
- Produces: no “Setup / finish setup”, “Configured”, “Managed · running” user-facing strings for Telegram

- [ ] **Step 1: Overview tile**

Replace the Telegram branch inside `tiles` `useMemo` with:

```ts
import {
  resolveTelegramAgentState,
  telegramOverviewCopy,
} from "@/features/connections/telegram/agent-state";

// inside tiles:
let telegramValue: string;
let telegramDetail: string;
if (statusUnavailable || !telegram) {
  telegramValue = "—";
  telegramDetail = "Status unavailable";
} else {
  const copy = telegramOverviewCopy(resolveTelegramAgentState(telegram));
  telegramValue = copy.value;
  telegramDetail = copy.detail;
}
```

Keep `href: "/connections/telegram"`.

- [ ] **Step 2: Health strip**

Replace `telegramChip` body (after unavailable/null checks) with:

```ts
import {
  resolveTelegramAgentState,
  telegramHealthChip,
} from "@/features/connections/telegram/agent-state";

const { statusLabel, tone } = telegramHealthChip(resolveTelegramAgentState(status.telegram));
return { key: "telegram", label: "Telegram", href, statusLabel, tone };
```

- [ ] **Step 3: Channel grid**

Replace configured/managed branches in `telegramCard` with:

```ts
import {
  resolveTelegramAgentState,
  telegramChannelCardCopy,
} from "@/features/connections/telegram/agent-state";

// after loading / unavailable / !status guards:
const copy = telegramChannelCardCopy(resolveTelegramAgentState(status));
return { badge: copy.badge, tone: copy.tone, description: copy.description };
```

Remove `runtimeLabel` import from `channel-grid.tsx` if unused.

- [ ] **Step 4: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/features/overview/overview-page.tsx frontend/features/overview/health-strip.tsx frontend/features/connections/channel-grid.tsx
git commit -m "$(cat <<'EOF'
feat(ui): align Overview Telegram status with agent vocabulary

EOF
)"
```

---

### Task 5: Backend always-on — verify / fix stuck Stopped

**Files:**
- Read/verify: `backend/src/personal_agent/presentation/web/app.py` (`should_autostart_telegram`, lifespan, `telegram_foreign_runtime_active`, `_telegram_runtime`, status `managed`)
- Modify only if bug found
- Test: `backend/tests/unit/test_telegram_autostart.py` (+ new cases if logic changes)

**Interfaces:**
- Consumes: existing worker + allowlist
- Produces: allowlisted dashboard reaches `managed=true` / listening runtime after process start when no foreign bot

- [ ] **Step 1: Reproduce with unit understanding**

Confirm current rules:

- Auto-start when `worker is not None` and `allowed` non-empty
- Skip start when `telegram_foreign_runtime_active` (audit phase in `starting|polling|responding|error` and worker not running)
- `managed` = `worker.running`

If last audit phase is a **fresh** `polling` from a dead process, auto-start is skipped forever → FE shows Starting. Fix: treat **stale** already (stale ∉ foreign set). If phase is non-stale foreign, keep skip.

- [ ] **Step 2: Add failing test only if changing behavior**

If you change foreign detection (example: also treat `stale` as not foreign — already true), or add ensure-start helper, extend `test_telegram_autostart.py`.

Example if adding `should_skip_autostart_for_foreign(runtime: str, worker_running: bool) -> bool` extracted for testability:

```python
def test_foreign_skip_only_for_live_foreign_phases():
    assert should_skip_autostart_for_foreign("polling", False) is True
    assert should_skip_autostart_for_foreign("stale", False) is False
    assert should_skip_autostart_for_foreign("stopped", False) is False
    assert should_skip_autostart_for_foreign("polling", True) is False
```

If no BE code change is required after reading, write a short note in the commit message of Task 6 verification instead — **do not invent a refactor**. Prefer extracting the boolean helper only when fixing a real skip bug.

- [ ] **Step 3: Minimal fix (only if needed)**

Allowed fixes:

1. Extract foreign-skip helper + correct phase set so auto-start is not blocked incorrectly
2. Ensure lifespan still calls `worker.start()` when `should_autostart_telegram` and not foreign
3. Do **not** add Start/Stop UI; do **not** remove existing API routes unless unused by FE (leave routes)

- [ ] **Step 4: Run BE tests**

```bash
cd backend && python -m pytest tests/unit/test_telegram_autostart.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit (skip commit if no BE file changes)**

```bash
git add backend/src/personal_agent/presentation/web/app.py backend/tests/unit/test_telegram_autostart.py
git commit -m "$(cat <<'EOF'
fix(telegram): keep always-on auto-start from getting stuck

EOF
)"
```

---

### Task 6: Verify + ship

**Files:** none new; verification only

- [ ] **Step 1: FE mapper tests**

```bash
cd frontend && node --experimental-strip-types --test features/connections/telegram/agent-state.test.ts
```

Expected: PASS.

- [ ] **Step 2: FE typecheck + format check**

```bash
cd frontend && npx tsc --noEmit && npm run format:check
```

Expected: clean.

- [ ] **Step 3: BE unit smoke**

```bash
cd backend && python -m pytest tests/unit/test_telegram_autostart.py tests/unit/test_telegram_reply_gate.py -v
```

Expected: PASS (reply gate unchanged).

- [ ] **Step 4: Manual prod/checklist after deploy**

1. Open `/connections/telegram` — see How it helps + How to use + one status word
2. Overview Telegram tile matches that status word
3. No “Connected · waiting” / “Status: Stopped” pair
4. Message bot with a question → activity shows Agent replied
5. Message “thanks” → Skipped (no reply needed)

- [ ] **Step 5: Push main for deploy (only if user asked / CI-on-push is the project norm and user wants ship)**

If shipping:

```bash
git push origin main
```

- [ ] **Step 6: Update spec status line**

In `docs/superpowers/specs/2026-11-11-aura-telegram-agent-clarity-design.md`, set:

`**Status:** Implemented`

Commit:

```bash
git add docs/superpowers/specs/2026-11-11-aura-telegram-agent-clarity-design.md
git commit -m "$(cat <<'EOF'
docs: mark Telegram agent clarity spec implemented

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
| --- | --- |
| Four-state vocabulary | Task 1 |
| Status panel one label/hint | Task 2 |
| How it helps / How to use / header | Task 3 |
| Activity preview preference + empty copy | Task 3 |
| Overview + health vocabulary | Task 4 |
| Channel grid alignment | Task 4 |
| Always-on / stuck Stopped | Task 5 |
| No start/stop/verify UI | All tasks (constraint) |
| Reply gate unchanged | Task 6 smoke |
| Success criteria verification | Task 6 |

## Plan self-review

- No TBD/placeholder steps
- Mapper signatures consistent across Tasks 1–4
- BE optional and gated on real stuck-Stopped bug
- TDD for mapper; FE has no Vitest — Node 22 strip-types test runner used instead
