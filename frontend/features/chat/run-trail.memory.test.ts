import { describe, expect, it } from "vitest";
import { applyRunEvent, emptyRunView } from "./run-trail";

describe("memory run events", () => {
  it("folds memory.proposed into a save proposal", () => {
    const view = applyRunEvent(emptyRunView, {
      seq: 1,
      run_id: "r1",
      type: "memory.proposed",
      data: { kind: "preference", content: "Prefers morning meetings", run_id: "r1" },
    });
    expect(view.memoryProposal).toEqual({
      kind: "preference",
      content: "Prefers morning meetings",
      source_run_id: "r1",
    });
  });

  it("folds memory.used chips", () => {
    const view = applyRunEvent(emptyRunView, {
      seq: 2,
      run_id: "r1",
      type: "memory.used",
      data: {
        items: [{ id: "m1", kind: "preference", content: "Prefers morning meetings" }],
      },
    });
    expect(view.usedMemories).toEqual([
      { id: "m1", kind: "preference", content: "Prefers morning meetings" },
    ]);
  });
});
