import { describe, expect, it } from "vitest";
import { badgeCount, expiresIn, itemKey, outcomeMessage, statusLabel } from "./inbox-logic";

describe("inbox logic", () => {
  it("never says an action happened when it is only waiting for approval", () => {
    expect(outcomeMessage("pending_approval")).toMatch(/Nothing has happened yet/);
    expect(outcomeMessage("done", "Task created")).toBe("Done. Task created");
    expect(outcomeMessage("acknowledged")).toMatch(/Nothing needed to run/);
  });

  it("labels statuses", () => {
    expect(statusLabel("new")).toBe("New");
    expect(statusLabel("expired")).toBe("Expired");
    expect(statusLabel("weird")).toBe("weird");
  });

  it("formats expiry countdowns and hides lapsed ones", () => {
    const now = Date.parse("2026-11-12T12:00:00Z");
    expect(expiresIn(null, now)).toBeNull();
    expect(expiresIn("2026-11-12T11:00:00Z", now)).toBeNull();
    expect(expiresIn("2026-11-12T12:20:00Z", now)).toBe("in 20m");
    expect(expiresIn("2026-11-12T15:00:00Z", now)).toBe("in 3h");
    expect(expiresIn("2026-11-16T12:00:00Z", now)).toBe("in 4d");
  });

  it("keys items by kind and id", () => {
    expect(itemKey({ kind: "approval", id: "a" })).toBe("approval-a");
    expect(itemKey({ kind: "suggestion", id: "a" })).toBe("suggestion-a");
  });

  it("prefers the inbox open count for the badge", () => {
    expect(badgeCount(4, 2)).toBe(4);
    expect(badgeCount(0, 2)).toBe(0);
    expect(badgeCount(null, 2)).toBe(2);
    expect(badgeCount(null, null)).toBeNull();
  });
});
