import { describe, expect, it } from "vitest";
import {
  insightLine,
  MAX_QUESTION_CHARS,
  MODULE_AGENTS,
  scopedPrompt,
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

  it("scopes the question to the module and keeps the user's words last", () => {
    const prompt = scopedPrompt("money", "  how much is left?  ");
    expect(prompt.startsWith("[Money agent] Use only my accounts")).toBe(true);
    expect(prompt.split("\n").at(-1)).toBe("how much is left?");
    expect(prompt).toContain("Never invent figures");
  });

  it("returns nothing for an empty question and caps long ones", () => {
    expect(scopedPrompt("plan", "   ")).toBe("");
    const long = scopedPrompt("plan", "x".repeat(MAX_QUESTION_CHARS + 50));
    expect(long.split("\n").at(-1)).toHaveLength(MAX_QUESTION_CHARS);
  });

  it("uses the page insight when there is one", () => {
    expect(insightLine("money", "Food is at 86%")).toBe("Food is at 86%");
    expect(insightLine("money", "  ")).toBe(MODULE_AGENTS.money.fallbackInsight);
    expect(insightLine("today", null)).toBe(MODULE_AGENTS.today.fallbackInsight);
  });
});
