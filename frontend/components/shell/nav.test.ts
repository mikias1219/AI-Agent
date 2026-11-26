import { describe, expect, it } from "vitest";
import { BOTTOM_NAV, isNavActive, MORE_NAV, NAV_GROUPS, NAV_ITEMS, titleForPath } from "./nav";

describe("personal-life nav", () => {
  it("groups Daily and Grow pages, then Agent and Settings; Chat is not a destination", () => {
    expect(NAV_GROUPS.map((g) => g.label)).toEqual(["Daily", "Grow", ""]);
    expect(NAV_GROUPS.map((g) => g.items.map((i) => i.label))).toEqual([
      ["Today", "Plan", "Money", "Needs you"],
      ["Learn", "Library"],
      ["Agent", "Settings"],
    ]);
  });

  it("shows counts on Plan, Needs you and Learn", () => {
    const keyed = NAV_ITEMS.filter((i) => "badgeKey" in i).map((i) => i.label);
    expect(keyed).toEqual(["Plan", "Needs you", "Learn"]);
  });

  it("keeps old chat links under Agent", () => {
    expect(isNavActive("/chat", "/agent")).toBe(true);
    expect(titleForPath("/chat")).toBe("Conversations");
  });

  it("titles every destination by its own label", () => {
    for (const item of NAV_ITEMS) {
      expect(titleForPath(item.href)).toBe(item.label);
    }
  });

  it("maps hub and child URLs to their destination title", () => {
    const cases: [string, string][] = [
      ["/goals", "Plan"],
      ["/habits", "Plan"],
      ["/review", "Plan"],
      ["/projects", "Plan"],
      ["/time", "Plan"],
      ["/money", "Money"],
      ["/calendar", "Plan"],
      ["/mail", "Needs you"],
      ["/library", "Library"],
      ["/library/notes/abc", "Library"],
      ["/learn", "Learn"],
      ["/learn/words", "Learn"],
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

  it("marks destinations active for their child paths", () => {
    expect(isNavActive("/goals", "/tasks")).toBe(true);
    expect(isNavActive("/calendar", "/tasks")).toBe(true);
    expect(isNavActive("/mail", "/inbox")).toBe(true);
    expect(isNavActive("/connections/mcp", "/agent")).toBe(true);
    expect(isNavActive("/library/files", "/library")).toBe(true);
    expect(isNavActive("/learn/reading", "/learn")).toBe(true);
    expect(isNavActive("/chat", "/")).toBe(false);
    expect(isNavActive("/library", "/learn")).toBe(false);
  });

  it("keeps Today, Plan, Money and Needs you around the central + and the rest in the menu", () => {
    expect(BOTTOM_NAV.map((i) => i.label)).toEqual(["Today", "Plan", "Money", "Needs you"]);
    expect(MORE_NAV.map((i) => i.label)).toEqual(["Learn", "Library", "Agent", "Settings"]);
  });
});
