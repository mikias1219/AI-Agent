"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { openQuickAdd } from "@/components/shell/quick-add-sheet";
import { moneyInsight } from "@/features/module-agent/insights";
import { ModuleAgent } from "@/features/module-agent/module-agent";
import { getMoneyAlerts, getMoneyInsights } from "@/lib/api/finance";
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
  // Accept the visible tab names too, so links like ?tab=activity open the right tab.
  const ALIASES: Record<string, string> = {
    activity: "transactions",
    budget: "budgets",
    savings: "goals",
  };
  const rawParam = params.get("tab") ?? "";
  const raw = ALIASES[rawParam] ?? rawParam;
  const tab = TABS.some((t) => t.id === raw) ? (raw as string) : "overview";
  const period = /^\d{4}-\d{2}$/.test(params.get("period") ?? "")
    ? (params.get("period") as string)
    : currentPeriod();

  function go(next: { tab?: string; period?: string }) {
    const query = new URLSearchParams({ tab: next.tab ?? tab, period: next.period ?? period });
    router.replace(`/money?${query}`, { scroll: false });
  }

  const needsMonth = !["goals", "periods", "income"].includes(tab);
  const [insight, setInsight] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  const loadInsight = useCallback(() => {
    Promise.all([getMoneyAlerts(), getMoneyInsights()])
      .then(([alerts, notes]) => setInsight(moneyInsight(alerts.budget, alerts.due, notes.items)))
      .catch(() => setInsight(null));
  }, []);

  useEffect(() => {
    loadInsight();
    const onChanged = () => {
      loadInsight();
      setVersion((v) => v + 1);
    };
    window.addEventListener("compass:data-changed", onChanged);
    return () => window.removeEventListener("compass:data-changed", onChanged);
  }, [loadInsight]);

  return (
    <div className="mx-auto flex w-full max-w-[var(--content-width)] flex-col gap-4">
      {/* Page header: title and the two money actions, same place on every tab. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-[length:var(--text-display,1.375rem)] font-semibold text-[var(--ink)]">
            Money
          </h1>
          <p className="text-[length:var(--text-caption)] text-[var(--muted)]">
            All amounts in ETB.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => openQuickAdd("income")}>
            Add income
          </Button>
          <Button onClick={() => openQuickAdd("expense")}>
            <Plus className="h-4 w-4" aria-hidden />
            Add expense
          </Button>
        </div>
      </div>
      <ModuleAgent
        module="money"
        insight={insight}
        action={
          tab === "budgets" ? null : { label: "Open budget", onClick: () => go({ tab: "budgets" }) }
        }
        onDataChanged={() => {
          loadInsight();
          setVersion((v) => v + 1);
        }}
      />
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
      <div key={version} className="contents">
        {tab === "overview" ? <OverviewTab period={period} /> : null}
        {tab === "periods" ? <PeriodTab /> : null}
        {tab === "income" ? <IncomeTab /> : null}
        {tab === "transactions" ? <TransactionsTab period={period} /> : null}
        {tab === "budgets" ? <BudgetTab period={period} /> : null}
        {tab === "goals" ? <GoalsTab /> : null}
      </div>
    </div>
  );
}
