import { describe, expect, it } from "vitest";
import { formatDate } from "./format-date";

describe("formatDate", () => {
  it("uses a month name so day and month cannot be confused", () => {
    expect(formatDate(new Date(2026, 10, 25))).toBe("25 Nov 2026");
  });
  it("returns the input for invalid dates", () => {
    expect(formatDate("nope")).toBe("nope");
  });
});
