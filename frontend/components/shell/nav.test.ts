import { describe, expect, it } from "vitest";
import { isNavActive, NAV_GROUPS, NAV_ITEMS, titleForPath } from "./nav";

describe("six-destination nav", () => {
  it("lists Today, Chat, Needs you, Plan, Agent, then Settings", () => {
    expect(NAV_GROUPS.map((g) => g.items.map((i) => i.label))).toEqual([
      ["Today", "Chat", "Needs you", "Plan", "Agent"],
      ["Settings"],
    ]);
  });

  it("titles every primary destination by its own label", () => {
    for (const item of NAV_ITEMS) {
      expect(titleForPath(item.href)).toBe(item.label);
    }
  });

  it("maps hub URLs to their destination title", () => {
    const cases: [string, string][] = [
      ["/goals", "Plan"],
      ["/calendar", "Plan"],
      ["/mail", "Needs you"],
      ["/agent", "Agent"],
      ["/routines", "Agent"],
      ["/activity", "Agent"],
      ["/connections", "Agent"],
      ["/connections/google", "Agent"],
      ["/help", "Help"],
    ];
    for (const [path, label] of cases) {
      expect(titleForPath(path)).toBe(label);
    }
  });

  it("marks Plan and Agent active for their child paths", () => {
    expect(isNavActive("/goals", "/tasks")).toBe(true);
    expect(isNavActive("/calendar", "/tasks")).toBe(true);
    expect(isNavActive("/mail", "/inbox")).toBe(true);
    expect(isNavActive("/connections/mcp", "/agent")).toBe(true);
    expect(isNavActive("/chat", "/")).toBe(false);
  });
});
