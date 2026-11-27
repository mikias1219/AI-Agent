import { describe, expect, it } from "vitest";
import { focusFirst } from "./focus-trap";

type Fake = { id: string; matches: string[]; focus: () => void };

/** A stand-in for a panel: each child lists which selector groups it matches. */
function panel(children: { id: string; kind: "field" | "button" | "auto-field" }[]) {
  let focused = "";
  const nodes: Fake[] = children.map((c) => ({
    id: c.id,
    matches:
      c.kind === "button" ? ["button"] : c.kind === "auto-field" ? ["field", "auto"] : ["field"],
    focus: () => {
      focused = c.id;
    },
  }));
  const root = {
    querySelector: (selector: string) => {
      if (selector === "[data-autofocus]")
        return nodes.find((n) => n.matches.includes("auto")) ?? null;
      if (selector.startsWith("input:not([disabled]):not")) {
        return nodes.find((n) => n.matches.includes("field")) ?? null;
      }
      return nodes[0] ?? null;
    },
    focus: () => {
      focused = "root";
    },
  };
  return { root: root as unknown as HTMLElement, focused: () => focused };
}

describe("focusFirst", () => {
  it("starts on the first field, not on the Close button", () => {
    const p = panel([
      { id: "close", kind: "button" },
      { id: "title", kind: "field" },
    ]);
    focusFirst(p.root);
    expect(p.focused()).toBe("title");
  });

  it("prefers an element marked data-autofocus", () => {
    const p = panel([
      { id: "close", kind: "button" },
      { id: "title", kind: "field" },
      { id: "body", kind: "auto-field" },
    ]);
    focusFirst(p.root);
    expect(p.focused()).toBe("body");
  });

  it("falls back to the first button when there is no field", () => {
    const p = panel([{ id: "close", kind: "button" }]);
    focusFirst(p.root);
    expect(p.focused()).toBe("close");
  });
});
