import { describe, expect, it } from "vitest";
import { taskListPath } from "../../lib/api/tasks";
import { dueInfo, toDateTimeLocal, viewParams } from "./task-views";

const now = new Date(2026, 10, 11, 12, 0, 0);

describe("viewParams", () => {
  it("maps views to API query params", () => {
    expect(viewParams("today")).toEqual({ view: "today" });
    expect(viewParams("upcoming")).toEqual({ view: "upcoming" });
    expect(viewParams("overdue")).toEqual({ view: "overdue" });
    expect(viewParams("done")).toEqual({ status: "done" });
    expect(viewParams("all")).toEqual({});
  });

  it("builds the list path", () => {
    expect(taskListPath()).toBe("/tasks");
    expect(taskListPath({ view: "overdue", priority: "p1" })).toBe(
      "/tasks?view=overdue&priority=p1",
    );
  });
});

describe("dueInfo", () => {
  it("returns null without a due date", () => {
    expect(dueInfo({ due_at: null, status: "planned" }, now)).toBeNull();
  });

  it("flags open past-due tasks as overdue", () => {
    const info = dueInfo(
      { due_at: new Date(2026, 10, 9, 9, 0).toISOString(), status: "planned" },
      now,
    );
    expect(info?.overdue).toBe(true);
    expect(info?.label).toMatch(/^Overdue/);
  });

  it("does not flag done tasks as overdue", () => {
    const info = dueInfo(
      { due_at: new Date(2026, 10, 9, 9, 0).toISOString(), status: "done" },
      now,
    );
    expect(info?.overdue).toBe(false);
  });

  it("labels today and tomorrow", () => {
    expect(
      dueInfo({ due_at: new Date(2026, 10, 11, 18, 0).toISOString(), status: "planned" }, now)
        ?.label,
    ).toMatch(/^Today/);
    expect(
      dueInfo({ due_at: new Date(2026, 10, 12).toISOString(), status: "planned" }, now)?.label,
    ).toBe("Tomorrow");
  });
});

describe("toDateTimeLocal", () => {
  it("formats local datetime and handles empty", () => {
    expect(toDateTimeLocal(new Date(2026, 10, 12, 9, 5).toISOString())).toBe("2026-11-12T09:05");
    expect(toDateTimeLocal(null)).toBe("");
  });
});
