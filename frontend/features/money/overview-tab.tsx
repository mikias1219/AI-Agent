"use client";

import { PiggyBank, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { KpiCard } from "@/components/ui/kpi-card";
import { StatusChip } from "@/components/ui/status-chip";
import { getSummary, monthlyReport } from "@/lib/api/finance";
import { budgetTone, formatAmount, formatMoney, periodLabel } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";
import { OccurrenceList } from "./occurrence-list";
import { QuickAdd } from "./quick-add";

const FILL = { green: "var(--success)", amber: "var(--warning)", red: "var(--danger)" } as const;

/** Rows share one grid so names, bars and numbers line up in every card. */
export const ROW_GRID = "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1";

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
  // Only months that have activity, so the chart never shows a wall of zeros.
  const months = (history.data?.rows ?? []).filter((r) => r.income_minor || r.spent_minor);
  const top = Math.max(1, ...months.map((m) => Math.max(m.income_minor, m.spent_minor)));

  return (
    <div className="flex flex-col gap-5">
      <Card id="money-add" title="Add money">
        <QuickAdd onSaved={reload} />
      </Card>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Income" value={formatAmount(s.income_minor)} icon={TrendingUp} />
        <KpiCard
          label="Spent"
          value={formatAmount(s.spent_minor)}
          icon={TrendingDown}
          upIsGood={false}
        />
        <KpiCard
          label="Left in budget"
          value={s.left_in_budget_minor === null ? "—" : formatAmount(s.left_in_budget_minor)}
          icon={Wallet}
          tone={
            s.left_in_budget_minor !== null && s.left_in_budget_minor < 0 ? "warning" : "default"
          }
          hint={s.budget ? undefined : "No budget yet"}
        />
        <KpiCard
          label="Saved"
          value={formatAmount(s.saved_minor)}
          icon={PiggyBank}
          hint={
            s.saved_minor > 0 ? `${Math.round(s.savings_rate_pct)}% of income` : "Nothing saved yet"
          }
        />
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <Card id="money-categories" title="Budget by category" description={periodLabel(period)}>
          {lines.length === 0 ? (
            <EmptyState
              compact
              title="No budget for this month"
              description="Create one in the Budget tab to see where you stand."
            />
          ) : (
            <ul className="flex flex-col gap-3.5">
              {lines.map((line) => (
                <li key={line.category_id} className={ROW_GRID}>
                  <span className="truncate text-sm text-[var(--ink)]">{line.category}</span>
                  <span className="flex items-center justify-end gap-2 text-xs text-[var(--muted)] tabular-nums">
                    {formatAmount(line.actual_minor)} / {formatAmount(line.planned_minor)}
                    {line.status !== "green" ? (
                      <StatusChip tone={budgetTone(line.status)}>
                        {Math.round(line.utilisation_pct)}%
                      </StatusChip>
                    ) : null}
                  </span>
                  <div
                    className="col-span-2 h-1.5 overflow-hidden rounded-full bg-[var(--subtle)]"
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
                        background: FILL[line.status],
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
              description="Add rent or salary in the Bills tab."
            />
          ) : (
            <OccurrenceList items={s.upcoming} onChange={reload} />
          )}
        </Card>
      </div>

      {months.length > 1 ? (
        <Card id="money-history" title="Income and spending by month">
          <div role="table" aria-label="Income and spending by month" className="text-sm">
            <div
              role="row"
              className="grid grid-cols-[3rem_1fr_5.5rem_5.5rem] gap-x-3 border-b border-[var(--border)] pb-2 text-xs text-[var(--muted)]"
            >
              <span role="columnheader">Month</span>
              <span role="columnheader" className="sr-only">
                Bar
              </span>
              <span role="columnheader" className="text-right">
                Income
              </span>
              <span role="columnheader" className="text-right">
                Spent
              </span>
            </div>
            {months.map((m) => (
              <div
                key={m.period}
                role="row"
                className="grid grid-cols-[3rem_1fr_5.5rem_5.5rem] items-center gap-x-3 border-b border-[var(--border)] py-2.5 last:border-0"
              >
                <span role="cell" className="text-[var(--muted)]">
                  {periodLabel(m.period).split(" ")[0].slice(0, 3)}
                </span>
                <span role="cell" className="flex flex-col gap-1">
                  <span
                    className="h-1.5 rounded-full bg-[var(--chart-1)]"
                    style={{ width: `${(m.income_minor / top) * 100}%` }}
                  />
                  <span
                    className="h-1.5 rounded-full bg-[var(--chart-4)]"
                    style={{ width: `${(m.spent_minor / top) * 100}%` }}
                  />
                </span>
                <span role="cell" className="text-right tabular-nums">
                  {formatAmount(m.income_minor)}
                </span>
                <span role="cell" className="text-right tabular-nums">
                  {formatAmount(m.spent_minor)}
                </span>
              </div>
            ))}
          </div>
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
