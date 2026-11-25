import { describe, expect, it } from "vitest";
import {
  addDays,
  canStep,
  clampDay,
  outcomeText,
  scorePercent,
  scoreWords,
  showWrapUp,
  suggestOutcome,
  summaryLine,
  toDateKey,
  weekDates,
} from "./day-logic";

describe("date maths", () => {
  it("formats and adds days across month ends", () => {
    expect(toDateKey(new Date(2026, 10, 5))).toBe("2026-11-05");
    expect(addDays("2026-11-30", 1)).toBe("2026-12-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });
  it("builds a Monday-first week", () => {
    const week = weekDates("2026-11-25");
    expect(week[0]).toBe("2026-11-23");
    expect(week[6]).toBe("2026-11-29");
    expect(weekDates("2026-11-29")[0]).toBe("2026-11-23");
  });
  it("clamps and bounds day switching", () => {
    expect(clampDay("nonsense", "2026-11-25")).toBe("2026-11-25");
    expect(clampDay("2000-01-01", "2026-11-25")).toBe(addDays("2026-11-25", -365));
    expect(canStep("2026-11-25", 1, "2026-11-25")).toBe(true);
    expect(canStep(addDays("2026-11-25", 365), 1, "2026-11-25")).toBe(false);
  });
});

describe("score", () => {
  it("words and percent", () => {
    expect(scorePercent(0.7)).toBe(70);
    expect(scorePercent(null)).toBeNull();
    expect(scoreWords(0.9)).toBe("Great day");
    expect(scoreWords(0.5)).toBe("Solid");
    expect(scoreWords(0.2)).toBe("Tough day, try again tomorrow");
    expect(scoreWords(null)).toBe("No score yet");
    expect(summaryLine(3, 5, 0.7)).toBe("Done 3 of 5, score 70%");
    expect(summaryLine(0, 0, null)).toBe("Done 0 of 0");
  });
});

describe("suggestOutcome", () => {
  it("maps actual against target", () => {
    expect(suggestOutcome(30, 30)).toBe("achieved");
    expect(suggestOutcome(40, 30)).toBe("achieved");
    expect(suggestOutcome(18, 30)).toBe("partial");
    expect(suggestOutcome(0, 30)).toBe("missed");
    expect(suggestOutcome(null, 30)).toBe("achieved");
    expect(suggestOutcome(5, null)).toBe("achieved");
  });
});

describe("outcomeText", () => {
  it("writes words, not colour", () => {
    expect(
      outcomeText({
        outcome: "achieved",
        actual_value: 30,
        target_value: 30,
        target_unit: "push-ups",
      }),
    ).toBe("Achieved 30/30 push-ups");
    expect(
      outcomeText({ outcome: "partial", actual_value: 18, target_value: 30, target_unit: "" }),
    ).toBe("Partly 18/30");
    expect(
      outcomeText({ outcome: "missed", actual_value: 0, target_value: 30, target_unit: "" }),
    ).toBe("Missed");
    expect(outcomeText({ outcome: "skipped" })).toBe("Skipped");
    expect(outcomeText({ outcome: "achieved" })).toBe("Achieved");
    expect(outcomeText({ outcome: null })).toBeNull();
  });
});

describe("showWrapUp", () => {
  it("needs evening and open tasks", () => {
    expect(showWrapUp(2, new Date(2026, 10, 25, 18))).toBe(true);
    expect(showWrapUp(0, new Date(2026, 10, 25, 18))).toBe(false);
    expect(showWrapUp(2, new Date(2026, 10, 25, 10))).toBe(false);
  });
});
