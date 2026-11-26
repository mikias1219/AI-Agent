"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { IconButton } from "@/components/ui/icon-button";
import { Tabs } from "@/components/ui/tabs";
import { currentPeriod, periodLabel, shiftPeriod } from "@/lib/money";
import { BillsTab } from "./bills-tab";
import { BudgetsTab } from "./budgets-tab";
import { GoalsTab } from "./goals-tab";
import { OverviewTab } from "./overview-tab";
import { TransactionsTab } from "./transactions-tab";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "transactions", label: "Transactions" },
  { id: "budgets", label: "Budgets" },
  { id: "bills", label: "Bills & income" },
  { id: "goals", label: "Goals" },
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

  const showMonth = tab === "overview" || tab === "transactions" || tab === "budgets";

  return (
    <div className="mx-auto flex w-full max-w-[var(--content-width)] flex-col gap-4">
      {showMonth ? (
        <div className="flex items-center gap-2">
          <IconButton
            label="Previous month"
            onClick={() => go({ period: shiftPeriod(period, -1) })}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
          </IconButton>
          <h1 className="min-w-36 text-center text-base font-semibold text-[var(--ink)]">
            {periodLabel(period)}
          </h1>
          <IconButton label="Next month" onClick={() => go({ period: shiftPeriod(period, 1) })}>
            <ChevronRight className="h-4 w-4" aria-hidden />
          </IconButton>
        </div>
      ) : null}
      <Tabs
        aria-label="Money sections"
        items={TABS}
        value={tab}
        onChange={(id) => go({ tab: id })}
        panels={{
          overview: <OverviewTab period={period} />,
          transactions: <TransactionsTab period={period} />,
          budgets: <BudgetsTab period={period} />,
          bills: <BillsTab />,
          goals: <GoalsTab />,
        }}
      />
    </div>
  );
}
