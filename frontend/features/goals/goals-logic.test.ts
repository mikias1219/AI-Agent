import { describe, expect, it } from "vitest";
import type { PlanStep } from "@/lib/api/goals";
import { approvalBreakdown, approvalNote, progressPercent, stepTone } from "./goals-logic";

function step(id: string, access_kind: PlanStep["access_kind"]): PlanStep {
  return { id, title: id, tool_name: null, access_kind, status: "planned", depends_on: [] };
}

describe("goals logic", () => {
  it("clamps progress to a whole percentage", () => {
    expect(progressPercent(0.456)).toBe(46);
    expect(progressPercent(2)).toBe(100);
    expect(progressPercent(-1)).toBe(0);
    expect(progressPercent(Number.NaN)).toBe(0);
  });

  it("counts hard-ceiling steps as still needing approval", () => {
    const plan = {
      steps: [
        step("a", "read"),
        step("b", "prepare"),
        step("c", "execute"),
        step("d", "destructive"),
      ],
    };
    expect(approvalBreakdown(plan)).toEqual({ authorized: 2, needsOk: 2 });
    expect(approvalNote(plan)).toContain("2 steps that send, change or delete still need your OK");
  });

  it("does not mention ceilings when there are none", () => {
    expect(approvalNote({ steps: [step("a", "read")] })).toBe("1 read/prepare step is authorized.");
  });

  it("flags needs_ok steps with a warning tone", () => {
    expect(stepTone("needs_ok")).toBe("warning");
    expect(stepTone("failed")).toBe("danger");
  });
});
