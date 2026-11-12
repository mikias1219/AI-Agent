import { describe, expect, it } from "vitest";
import type { GoogleEvent } from "@/lib/api/google";
import { bucketWeek, formatEventTime, isAllDay, parseStart } from "./calendar-logic";

const ev = (id: string, startsAt: string): GoogleEvent => ({
  id,
  title: id,
  startsAt,
  location: "",
});

describe("calendar logic", () => {
  it("treats bare dates as local all-day events", () => {
    expect(isAllDay("2026-11-12")).toBe(true);
    expect(isAllDay("2026-11-12T09:00:00Z")).toBe(false);
    const d = parseStart("2026-11-12");
    expect(d?.getDate()).toBe(12);
    expect(formatEventTime("2026-11-12")).toBe("All day");
  });

  it("buckets events by day, sorted, with later and undated kept separate", () => {
    const from = new Date(2026, 10, 12, 8, 0);
    const result = bucketWeek(
      [
        ev("late", "2026-11-12T15:00:00"),
        ev("early", "2026-11-12T09:00:00"),
        ev("next", "2026-11-14T10:00:00"),
        ev("far", "2026-12-30T10:00:00"),
        ev("past", "2026-11-01T10:00:00"),
        ev("none", ""),
      ],
      from,
    );
    expect(result.days).toHaveLength(7);
    expect(result.days[0].events.map((e) => e.id)).toEqual(["early", "late"]);
    expect(result.days[2].events.map((e) => e.id)).toEqual(["next"]);
    expect(result.later.map((e) => e.id)).toEqual(["far"]);
    expect(result.undated.map((e) => e.id)).toEqual(["none"]);
  });
});
