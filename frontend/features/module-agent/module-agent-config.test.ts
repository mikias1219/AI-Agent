import { describe, expect, it } from "vitest";
import {
  agentContext,
  cleanQuestion,
  insightLine,
  MAX_QUESTION_CHARS,
  MODULE_AGENTS,
  moduleForPath,
} from "./module-agent-config";

describe("module agents", () => {
  it("has one agent per module with at most four chips", () => {
    expect(Object.keys(MODULE_AGENTS)).toEqual(["today", "plan", "money", "learn", "library"]);
    for (const config of Object.values(MODULE_AGENTS)) {
      expect(config.chips.length).toBeGreaterThan(0);
      expect(config.chips.length).toBeLessThanOrEqual(4);
      expect(config.name).toMatch(/agent$/);
    }
  });

  it("puts the scope in hidden context, not in the question", () => {
    const context = agentContext("money", "Saved accounts: Salary.");
    expect(context).toContain("Use only their accounts");
    expect(context).toContain("Never invent figures");
    expect(context.split("\n").at(-1)).toBe("Saved accounts: Salary.");
    expect(cleanQuestion("  how much is left?  ")).toBe("how much is left?");
  });

  it("returns nothing for an empty question and caps long input", () => {
    expect(cleanQuestion("   ")).toBe("");
    expect(cleanQuestion("x".repeat(MAX_QUESTION_CHARS + 50))).toHaveLength(MAX_QUESTION_CHARS);
    expect(agentContext("learn", "y".repeat(5000)).length).toBeLessThanOrEqual(4000);
  });

  it("uses the page insight when there is one", () => {
    expect(insightLine("money", "Food is at 86%")).toBe("Food is at 86%");
    expect(insightLine("money", "  ")).toBe(MODULE_AGENTS.money.fallbackInsight);
    expect(insightLine("today", null)).toBe(MODULE_AGENTS.today.fallbackInsight);
  });

  it("finds the module agent for a path", () => {
    expect(moduleForPath("/")).toBe("today");
    expect(moduleForPath("/habits")).toBe("plan");
    expect(moduleForPath("/money")).toBe("money");
    expect(moduleForPath("/library/notes/x")).toBe("library");
    expect(moduleForPath("/inbox")).toBeNull();
  });
});
