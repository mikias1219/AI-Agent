import { describe, expect, it } from "vitest";
import { formatMinutes } from "./api/time";

describe("formatMinutes", () => {
  it("reads naturally", () => {
    expect(formatMinutes(45)).toBe("45 min");
    expect(formatMinutes(60)).toBe("1 h");
    expect(formatMinutes(135)).toBe("2 h 15 min");
  });
});
