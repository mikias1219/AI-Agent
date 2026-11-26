import { describe, expect, it } from "vitest";
import { budgetTone, currentPeriod, formatMoney, parseAmount, shiftPeriod } from "./money";

describe("money helpers", () => {
  it("formats minor units", () => {
    expect(formatMoney(25000)).toBe("250 ETB");
    expect(formatMoney(25050)).toBe("250.50 ETB");
    expect(formatMoney(-1234500, "USD")).toBe("-12,345 USD");
  });
  it("parses typed amounts strictly", () => {
    expect(parseAmount("1,250.5")).toBe(1250.5);
    expect(parseAmount("250")).toBe(250);
    for (const bad of ["", "abc", "0", "-5", "1.234"]) expect(parseAmount(bad)).toBeNull();
  });
  it("shifts periods across years", () => {
    expect(shiftPeriod("2026-12", 1)).toBe("2027-01");
    expect(shiftPeriod("2026-01", -1)).toBe("2025-12");
    expect(currentPeriod(new Date(2026, 10, 26))).toBe("2026-11");
  });
  it("maps budget status to chip tones", () => {
    expect(budgetTone("red")).toBe("danger");
    expect(budgetTone("amber")).toBe("warning");
    expect(budgetTone("green")).toBe("success");
  });
});
