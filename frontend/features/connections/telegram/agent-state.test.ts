import { expect, test } from "vitest";
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
  expect(resolveTelegramAgentState(base({ configured: false, allowed_chat_ids: [] }))).toBe(
    "needs_setup",
  );
});

test("needs_setup when allowlist empty", () => {
  expect(resolveTelegramAgentState(base({ allowed_chat_ids: [] }))).toBe("needs_setup");
});

test("error when runtime is error", () => {
  expect(resolveTelegramAgentState(base({ runtime: "error" }))).toBe("error");
});

test("listening for polling/responding/running", () => {
  for (const runtime of ["polling", "responding", "running"]) {
    expect(resolveTelegramAgentState(base({ runtime, managed: true }))).toBe("listening");
  }
});

test("listening when managed even if runtime is starting", () => {
  expect(resolveTelegramAgentState(base({ managed: true, runtime: "starting" }))).toBe("listening");
});

test("starting when allowlisted but not yet listening", () => {
  expect(resolveTelegramAgentState(base({ runtime: "stopped", managed: false }))).toBe("starting");
  expect(resolveTelegramAgentState(base({ runtime: "unknown", managed: false }))).toBe("starting");
  expect(resolveTelegramAgentState(base({ runtime: "stale", managed: false }))).toBe("starting");
  expect(resolveTelegramAgentState(base({ runtime: "starting", managed: false }))).toBe("starting");
  for (const runtime of ["polling", "responding", "running"]) {
    expect(resolveTelegramAgentState(base({ runtime, managed: false }))).toBe("starting");
  }
});

test("labels and overview copy match vocabulary", () => {
  expect(telegramAgentStatusLabel("listening")).toBe("Listening");
  expect(telegramOverviewCopy("needs_setup").value).toBe("Needs setup");
  expect(telegramOverviewCopy("listening").detail).toBe("Agent replies in Telegram");
});
