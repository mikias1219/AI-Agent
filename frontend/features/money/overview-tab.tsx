"use client";

import { PiggyBank, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { KpiCard } from "@/components/ui/kpi-card";
import { StatusChip } from "@/components/ui/status-chip";
import { getSummary, monthlyReport } from "@/lib/api/finance";
import { budgetTone, formatMoney, periodLabel } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";
import { OccurrenceList } from "./occurrence-list";
import { QuickAdd } from "./quick-add";

export function OverviewTab({ period }: { period: string }) {
  const summary = useLoad(() => getSummary(period), [period]);
  const history = useLoad(() => monthlyReport(6));
  const reload = () => {
    void summary.reload();
    void history.reload();
  };

  if (summary.error) return <ErrorBlock what="money" message={summary.error} onRetry={reload} />;
  if (!summary.data) return <CardSkeleton rows={5} />;
  const s = summary.data;
  const lines = s.budget?.lines ?? [];

  return (
    <div className="flex flex-col gap-5">
      <Card id="money-add" title="Add money">
        <QuickAdd onSaved={reload} />
      </Card>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Income received" value={formatMoney(s.income_minor)} icon={TrendingUp} />
        <KpiCard
          label="Spent"
          value={formatMoney(s.spent_minor)}
          icon={TrendingDown}
          upIsGood={false}
        />
        <KpiCard
          label="Left in budget"
          value={
            s.left_in_budget_minor === null ? "No budget" : formatMoney(s.left_in_budget_minor)
          }
          icon={Wallet}
          tone={
            s.left_in_budget_minor !== null && s.left_in_budget_minor < 0 ? "warning" : "default"
          }
          hint={s.budget ? undefined : "Set one in Budgets"}
        />
        <KpiCard
          label="Saved"
          value={formatMoney(s.saved_minor)}
          icon={PiggyBank}
          hint={s.income_minor > 0 ? `${s.savings_rate_pct}% savings rate` : undefined}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card id="money-categories" title="Budget by category" description={periodLabel(period)}>
          {lines.length === 0 ? (
            <EmptyState
              compact
              title="No budget for this month"
              description="Create one in the Budgets tab to see where you stand."
            />
          ) : (
            <ul className="flex flex-col gap-3">
              {lines.map((line) => (
                <li key={line.category_id} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate text-[var(--ink)]">{line.category}</span>
                    <span className="flex items-center gap-2 text-xs text-[var(--muted)] tabular-nums">
                      {formatMoney(line.actual_minor)} / {formatMoney(line.planned_minor)}
                      {line.status !== "green" ? (
                        <StatusChip tone={budgetTone(line.status)}>
                          {Math.round(line.utilisation_pct)}%
                        </StatusChip>
                      ) : null}
                    </span>
                  </div>
                  <div
                    className="h-2 overflow-hidden rounded-full bg-[var(--subtle)]"
                    role="progressbar"
                    aria-label={`${line.category} used`}
                    aria-valuenow={Math.min(Math.round(line.utilisation_pct), 100)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.min(line.utilisation_pct, 100)}%`,
                        background: `var(--${line.status === "red" ? "danger" : line.status === "amber" ? "warning" : "success"})`,
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card id="money-upcoming" title="Next 14 days" description="Bills and income due soon.">
          {s.upcoming.length === 0 ? (
            <EmptyState
              compact
              title="Nothing due"
              description="Add rent, salary or other repeating items in Bills & income."
            />
          ) : (
            <OccurrenceList items={s.upcoming} onChange={reload} />
          )}
        </Card>
      </div>

      {history.data && history.data.rows.some((r) => r.income_minor || r.spent_minor) ? (
        <Card id="money-history" title="Income vs spending" description="Last 6 months.">
          <ul className="flex flex-col gap-3" aria-label="Income and spending per month">
            {history.data.rows.map((r) => {
              const top = Math.max(
                ...history.data!.rows.map((x) => Math.max(x.income_minor, x.spent_minor)),
                1,
              );
              return (
                <li
                  key={r.period}
                  className="grid grid-cols-[3.5rem_1fr] items-center gap-3 text-xs"
                >
                  <span className="text-[var(--muted)]">
                    {periodLabel(r.period).split(" ")[0].slice(0, 3)}
                  </span>
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 rounded-full bg-[var(--chart-1)]"
                        style={{ width: `${(r.income_minor / top) * 100}%` }}
                      />
                      <span className="tabular-nums text-[var(--muted)]">
                        {formatMoney(r.income_minor)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 rounded-full bg-[var(--chart-4)]"
                        style={{ width: `${(r.spent_minor / top) * 100}%` }}
                      />
                      <span className="tabular-nums text-[var(--muted)]">
                        {formatMoney(r.spent_minor)}
                      </span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 flex gap-4 text-xs text-[var(--muted)]">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[var(--chart-1)]" />
              Income
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[var(--chart-4)]" />
              Spent
            </span>
          </p>
        </Card>
      ) : null}
    </div>
  );
}
