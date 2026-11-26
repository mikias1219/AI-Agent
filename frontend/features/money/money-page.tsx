"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { IconButton } from "@/components/ui/icon-button";
import { Tabs } from "@/components/ui/tabs";
import { currentPeriod, periodLabel, shiftPeriod } from "@/lib/money";
import { BudgetTab } from "./budget-tab";
import { GoalsTab } from "./goals-tab";
import { IncomeTab } from "./income-tab";
import { PeriodTab } from "./period-tab";
import { OverviewTab } from "./overview-tab";
import { TransactionsTab } from "./transactions-tab";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "periods", label: "By period" },
  { id: "income", label: "Income" },
  { id: "transactions", label: "Activity" },
  { id: "budgets", label: "Budget" },
  { id: "goals", label: "Savings" },
];

/** Money: one month at a time. The month switcher drives Overview, Transactions and Budgets. */
export function MoneyPage() {
  const router = useRouter();
  const params = useSearchParams();
  const raw = params.get("tab");
  const tab = TABS.some((t) => t.id === raw) ? (raw as string) : "overview";
  const period = /^\d{4}-\d{2}$/.test(params.get("period") ?? "")
    ? (params.get("period") as string)
    : currentPeriod();

  function go(next: { tab?: string; period?: string }) {
    const query = new URLSearchParams({ tab: next.tab ?? tab, period: next.period ?? period });
    router.replace(`/money?${query}`, { scroll: false });
  }

  const needsMonth = !["goals", "periods", "income"].includes(tab);

  return (
    <div className="mx-auto flex w-full max-w-[var(--content-width)] flex-col gap-4">
      {/* One fixed header row: tabs left, month right. It never appears or disappears. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs
          aria-label="Money sections"
          items={TABS}
          value={tab}
          onChange={(id) => go({ tab: id })}
        />
        <div
          className={`flex items-center gap-1 ${needsMonth ? "" : "invisible"}`}
          aria-hidden={!needsMonth}
        >
          <IconButton
            label="Previous month"
            disabled={!needsMonth}
            onClick={() => go({ period: shiftPeriod(period, -1) })}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
          </IconButton>
          <span className="min-w-32 text-center text-sm font-semibold text-[var(--ink)]">
            {periodLabel(period)}
          </span>
          <IconButton
            label="Next month"
            disabled={!needsMonth}
            onClick={() => go({ period: shiftPeriod(period, 1) })}
          >
            <ChevronRight className="h-4 w-4" aria-hidden />
          </IconButton>
        </div>
      </div>
      <p className="-mt-2 text-xs text-[var(--muted)]">All amounts in ETB.</p>
      {tab === "overview" ? <OverviewTab period={period} /> : null}
      {tab === "periods" ? <PeriodTab /> : null}
      {tab === "income" ? <IncomeTab /> : null}
      {tab === "transactions" ? <TransactionsTab period={period} /> : null}
      {tab === "budgets" ? <BudgetTab period={period} /> : null}
      {tab === "goals" ? <GoalsTab /> : null}
    </div>
  );
}
