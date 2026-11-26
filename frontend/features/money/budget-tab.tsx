"use client";

import { BillsTab } from "./bills-tab";
import { BudgetsTab } from "./budgets-tab";

/** The month's plan in one place: what comes in and goes out on a date, then the spending limits. */
export function BudgetTab({ period }: { period: string }) {
  return (
    <div className="flex flex-col gap-5">
      <BillsTab />
      <BudgetsTab period={period} />
    </div>
  );
}
