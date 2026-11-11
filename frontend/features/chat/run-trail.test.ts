import { describe, expect, it } from "vitest";
import type { RunEvent } from "../../lib/api/types";
import {
  applyRunEvent,
  emptyRunView,
  formatDuration,
  isTerminal,
  stepLabel,
  trailSummary,
  type RunView,
} from "./run-trail";

function ev(type: RunEvent["type"], data: Record<string, unknown> = {}): RunEvent {
  return { seq: 0, run_id: "r1", type, data };
}

function fold(events: RunEvent[]): RunView {
  return events.reduce(applyRunEvent, emptyRunView);
}

describe("applyRunEvent", () => {
  it("builds the step trail and final answer in event order", () => {
    const view = fold([
      ev("run.started", { session_id: "s1" }),
      ev("tool.started", { call_id: "c1", name: "task_create", arguments: {} }),
      ev("tool.finished", { call_id: "c1", ok: true, output: "Created", duration_ms: 42 }),
      ev("token", { text: "Done" }),
      ev("run.completed", { reply: "Done. Task created.", stop_reason: null }),
    ]);
    expect(view.sessionId).toBe("s1");
    expect(view.steps).toEqual([
      { id: "c1", name: "task_create", status: "ok", durationMs: 42, detail: "Created" },
    ]);
    expect(view.content).toBe("Done. Task created.");
    expect(view.status).toBe("completed");
    expect(isTerminal(view)).toBe(true);
  });

  it("marks failed tools and keeps the run going", () => {
    const view = fold([
      ev("tool.started", { call_id: "c1", name: "ghost" }),
      ev("tool.finished", { call_id: "c1", ok: false, output: "No tool named ghost" }),
    ]);
    expect(view.steps[0]).toMatchObject({ status: "failed", detail: "No tool named ghost" });
    expect(view.status).toBe("running");
  });

  it("shows approval state on the waiting step", () => {
    const waiting = fold([
      ev("tool.started", { call_id: "c1", name: "send_email" }),
      ev("approval.required", { approval_id: "a1" }),
    ]);
    expect(waiting.steps[0].approval).toBe("waiting");
    const resolved = applyRunEvent(waiting, ev("approval.resolved", { decision: "denied" }));
    expect(resolved.steps[0].approval).toBe("denied");
  });

  it("treats a cancelled run.failed as stopped, keeping the summary", () => {
    const view = fold([
      ev("token", { text: "Hel" }),
      ev("run.failed", { status: "cancelled", reply: "I stopped because you asked me to." }),
    ]);
    expect(view.status).toBe("cancelled");
    expect(view.content).toBe("I stopped because you asked me to.");
  });

  it("surfaces real failures with their message", () => {
    const view = fold([ev("run.failed", { status: "failed", error: "model offline" })]);
    expect(view).toMatchObject({ status: "failed", error: "model offline" });
  });

  it("keeps the limit stop reason", () => {
    const view = fold([
      ev("run.completed", { reply: "I stopped after 6 tool rounds", stop_reason: "limit_rounds" }),
    ]);
    expect(view.stopReason).toBe("limit_rounds");
  });
});

describe("labels", () => {
  it("formats step names, durations and summaries", () => {
    expect(stepLabel("task_create")).toBe("Task create");
    expect(formatDuration(850)).toBe("850 ms");
    expect(formatDuration(1500)).toBe("1.5 s");
    expect(trailSummary([], true)).toBe("Working…");
    expect(trailSummary([{ id: "a", name: "x", status: "ok" }], true)).toBe("Working… 1 step");
    expect(
      trailSummary(
        [
          { id: "a", name: "x", status: "ok" },
          { id: "b", name: "y", status: "ok" },
        ],
        false,
      ),
    ).toBe("Used 2 tools");
  });
});
