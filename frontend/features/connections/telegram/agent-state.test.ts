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
  assert.equal(
    resolveTelegramAgentState(base({ managed: true, runtime: "starting" })),
    "listening",
  );
});

test("starting when allowlisted but not yet listening", () => {
  assert.equal(resolveTelegramAgentState(base({ runtime: "stopped", managed: false })), "starting");
  assert.equal(resolveTelegramAgentState(base({ runtime: "unknown", managed: false })), "starting");
  assert.equal(resolveTelegramAgentState(base({ runtime: "stale", managed: false })), "starting");
  assert.equal(
    resolveTelegramAgentState(base({ runtime: "starting", managed: false })),
    "starting",
  );
});

test("labels and overview copy match vocabulary", () => {
  assert.equal(telegramAgentStatusLabel("listening"), "Listening");
  assert.equal(telegramOverviewCopy("needs_setup").value, "Needs setup");
  assert.equal(telegramOverviewCopy("listening").detail, "Agent replies in Telegram");
});
