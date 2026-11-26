import { describe, expect, it } from "vitest";
import type { BudgetAlert, Occurrence } from "@/lib/api/finance";
import { moneyInsight, planInsight } from "./insights";

const alert = (over: Partial<BudgetAlert>): BudgetAlert => ({
  category: "Food",
  status: "amber",
  utilisation_pct: 86.4,
  remaining_minor: 50_000,
  days_left: 9,
  ...over,
});
const occ = (over: Partial<Occurrence>): Occurrence => ({
  id: "o1",
  rule_id: "r1",
  title: "Rent",
  kind: "bill",
  due_date: "2026-12-01",
  expected_minor: 800_000,
  paid_minor: 0,
  remaining_minor: 800_000,
  status: "expected",
  ...over,
});

describe("moneyInsight", () => {
  it("puts an overspent category first", () => {
    const line = moneyInsight([alert({}), alert({ category: "Taxi", status: "red" })], [], []);
    expect(line).toBe("Taxi is over budget with 9 days left.");
  });

  it("then overdue bills, then pace warnings, then near-limit budgets", () => {
    expect(moneyInsight([alert({})], [occ({ status: "overdue" })], [])).toMatch(/^Rent is overdue/);
    expect(
      moneyInsight([alert({})], [], [{ kind: "pace", severity: "warning", message: "Too fast." }]),
    ).toBe("Too fast.");
    expect(moneyInsight([alert({})], [], [])).toBe("Food is at 86% of budget with 9 days left.");
  });

  it("mentions upcoming bills and expected income, and is null when calm", () => {
    expect(moneyInsight([], [occ({})], [])).toMatch(/^Rent is due 2026-12-01/);
    expect(moneyInsight([], [occ({ kind: "income", title: "Salary" })], [])).toBe(
      "Salary is expected today. Did it arrive?",
    );
    expect(moneyInsight([], [], [])).toBeNull();
  });
});

describe("planInsight", () => {
  it("counts tasks left and those without a time", () => {
    expect(planInsight(null, 0)).toBeNull();
    expect(planInsight(0, 0)).toBe("Everything planned for today is done.");
    expect(planInsight(1, 0)).toBe("1 task left today.");
    expect(planInsight(10, 5)).toBe("10 tasks left today, 5 without a time.");
  });
});
