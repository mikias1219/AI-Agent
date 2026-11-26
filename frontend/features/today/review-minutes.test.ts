import { describe, expect, it } from "vitest";
import { reviewMinutes } from "./today-logic";

describe("reviewMinutes", () => {
  it("is about 20 seconds a word and never below one minute", () => {
    expect(reviewMinutes(13)).toBe(4);
    expect(reviewMinutes(1)).toBe(1);
    expect(reviewMinutes(60)).toBe(20);
  });
});
