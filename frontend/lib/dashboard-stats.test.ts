import { describe, expect, it } from "vitest";
import type { ActivityEvent } from "@/lib/api/types";
import {
  breakdown,
  bucketByDay,
  groupForEvent,
  isHousekeeping,
  percentChange,
} from "./dashboard-stats";

const NOW = new Date(2026, 10, 25, 12, 0, 0);

function ev(id: number, event: string, daysAgo: number): ActivityEvent {
  const when = new Date(2026, 10, 25 - daysAgo, 9, 0, 0);
  return { id, occurred_at: when.toISOString(), actor: "agent", event, details: {} };
}

describe("dashboard stats", () => {
  it("groups audit events", () => {
    expect(groupForEvent("run.completed")).toBe("completed");
    expect(groupForEvent("run.cancelled")).toBe("failed");
    expect(groupForEvent("approval.decided")).toBe("approvals");
    expect(groupForEvent("reminder.delivered")).toBe("routines");
    expect(groupForEvent("tool.x")).toBe("other");
    expect(groupForEvent("task.created")).toBe("tasks");
    expect(groupForEvent("chat.user_message")).toBe("messages");
  });

  it("does not count system housekeeping as agent actions", () => {
    expect(isHousekeeping("telegram.runtime")).toBe(true);
    expect(isHousekeeping("scheduler.tick")).toBe(true);
    expect(isHousekeeping("run.completed")).toBe(false);
    const buckets = bucketByDay(
      [ev(1, "telegram.runtime", 0), ev(2, "scheduler.tick", 0), ev(3, "task.created", 0)],
      7,
      NOW,
    );
    expect(buckets[6]!.total).toBe(1);
    expect(buckets[6]!.counts.tasks).toBe(1);
  });

  it("buckets by local day, oldest first, ignoring events outside the window", () => {
    const buckets = bucketByDay(
      [
        ev(1, "run.completed", 0),
        ev(2, "run.completed", 0),
        ev(3, "run.failed", 2),
        ev(4, "run.completed", 30),
      ],
      7,
      NOW,
    );
    expect(buckets).toHaveLength(7);
    expect(buckets[6]!.total).toBe(2);
    expect(buckets[4]!.counts.failed).toBe(1);
    expect(buckets.reduce((n, b) => n + b.total, 0)).toBe(3);
  });

  it("breaks down totals largest first", () => {
    const buckets = bucketByDay(
      [ev(1, "run.completed", 0), ev(2, "run.completed", 1), ev(3, "approval.decided", 1)],
      7,
      NOW,
    );
    expect(breakdown(buckets).map((b) => [b.key, b.value])).toEqual([
      ["completed", 2],
      ["approvals", 1],
    ]);
  });

  it("has no percent change without a baseline", () => {
    expect(percentChange(5, 0)).toBeNull();
    expect(percentChange(15, 10)).toBe(50);
    expect(percentChange(5, 10)).toBe(-50);
  });
});
