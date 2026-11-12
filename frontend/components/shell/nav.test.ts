import { describe, expect, it } from "vitest";
import { isNavActive, NAV_GROUPS, NAV_ITEMS, titleForPath } from "./nav";

describe("nav", () => {
  it("groups destinations as Today/Chat/Inbox, My work, AURA, footer", () => {
    expect(NAV_GROUPS.map((g) => g.items.map((i) => i.label))).toEqual([
      ["Today", "Chat", "Inbox"],
      ["Tasks", "Goals", "Calendar", "Mail"],
      ["Memory", "Routines", "Activity"],
      ["Connections", "Settings", "Help"],
    ]);
  });

  it("titles and activates every href", () => {
    for (const item of NAV_ITEMS) {
      expect(titleForPath(item.href)).toBe(item.label);
      expect(titleForPath(`${item.href === "/" ? "" : item.href}/child`)).toBe(
        item.href === "/" ? "Today" : item.label,
      );
      expect(isNavActive(item.href, item.href)).toBe(true);
    }
  });

  it("keeps Today active only on the root and titles the legacy automations path", () => {
    expect(isNavActive("/chat", "/")).toBe(false);
    expect(titleForPath("/automations")).toBe("Routines");
  });
});
