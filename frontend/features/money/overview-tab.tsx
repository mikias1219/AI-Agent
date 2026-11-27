"use client";

import Link from "next/link";
import { CheckCircle2, PiggyBank, TrendingDown, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { KpiCard } from "@/components/ui/kpi-card";
import { StatusChip } from "@/components/ui/status-chip";
import {
  categoryReport,
  getCategories,
  getSummary,
  listTransactions,
  monthlyReport,
} from "@/lib/api/finance";
import { budgetTone, daysLeftInPeriod, formatAmount, formatMoney, periodLabel } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";
import { dueLabel } from "./occurrence-list";
import { TxRow } from "./tx-row";

const FILL = { green: "var(--success)", amber: "var(--warning)", red: "var(--danger)" } as const;

/** A row with a name on the left, a figure on the right and a bar underneath. */
function BarRow({
  name,
  figure,
  pct,
  color,
}: {
  name: string;
  figure: string;
  pct: number;
  color: string;
}) {
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1">
      <span className="truncate text-sm text-[var(--ink)]">{name}</span>
      <span className="text-right text-xs text-[var(--muted)] tabular-nums">{figure}</span>
      <div
        className="col-span-2 h-1.5 overflow-hidden rounded-full bg-[var(--subtle)]"
        role="progressbar"
        aria-label={name}
        aria-valuenow={Math.min(Math.round(pct), 100)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${Math.min(pct, 100)}%`, background: color }}
        />
      </div>
    </li>
  );
}

/**
 * The month at a glance, in the order you think about it: how much is left, what needs
 * attention, where the money went, what just happened.
 */
export function OverviewTab({ period }: { period: string }) {
  const summary = useLoad(() => getSummary(period), [period]);
  const spend = useLoad(() => categoryReport(period), [period]);
  const recent = useLoad(() => listTransactions({ period }), [period]);
  const categories = useLoad(getCategories);
  const history = useLoad(() => monthlyReport(6));
  const reload = () => {
    void summary.reload();
    void spend.reload();
    void recent.reload();
    void history.reload();
  };

  if (summary.error) return <ErrorBlock what="money" message={summary.error} onRetry={reload} />;
  if (!summary.data) return <CardSkeleton rows={5} />;
  const s = summary.data;
  const names = new Map((categories.data ?? []).map((c) => [c.id, c.name]));

  const planned = s.budget_planned_minor;
  const used = s.spent_minor + s.saved_minor;
  const usedPct = planned > 0 ? (used / planned) * 100 : 0;
  const left = s.left_in_budget_minor;
  const days = daysLeftInPeriod(period);
  const perDay = left !== null && left > 0 && days > 0 ? Math.floor(left / days) : null;

  const attention = [
    ...(s.budget?.lines ?? [])
      .filter((l) => l.status !== "green")
      .map((l) => ({
        key: `c-${l.category_id}`,
        text: `${l.category} is at ${Math.round(l.utilisation_pct)}%`,
        tone: budgetTone(l.status),
        hint: l.remaining_minor >= 0 ? `${formatAmount(l.remaining_minor)} left` : "over budget",
      })),
    ...s.upcoming
      .filter((o) => o.status === "overdue" || o.status === "partial" || isSoon(o.due_date))
      .map((o) => ({
        key: `o-${o.id}`,
        text: `${o.title} ${o.kind === "income" ? "expected" : "due"} ${dueLabel(o.due_date)}`,
        tone: (o.status === "overdue" ? "danger" : "warning") as "danger" | "warning",
        hint: formatMoney(o.remaining_minor),
      })),
  ];

  const top = (spend.data?.rows ?? []).filter((r) => r.amount_minor > 0).slice(0, 5);
  const topMax = Math.max(1, ...top.map((r) => r.amount_minor));
  const months = (history.data?.rows ?? []).filter((r) => r.income_minor || r.spent_minor);

  return (
    <div className="flex flex-col gap-5">
      <Card id="money-left" title="Left this month" description={`${periodLabel(period)} · ETB`}>
        {left === null ? (
          <EmptyState
            compact
            title="No budget for this month"
            description="Set spending limits to see what is left and what you can spend each day."
            action={
              <Link
                href={`/money?tab=budgets&period=${period}`}
                className="text-sm font-medium text-[var(--accent)] hover:underline"
              >
                Set a budget
              </Link>
            }
          />
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-1">
              <p
                className={`text-4xl leading-none font-semibold tracking-tight tabular-nums ${left < 0 ? "text-[var(--danger)]" : "text-[var(--ink)]"}`}
              >
                {formatAmount(left)}
              </p>
              <p className="text-sm text-[var(--muted)]">
                {perDay !== null
                  ? `About ${formatAmount(perDay)} a day for ${days} more ${days === 1 ? "day" : "days"}`
                  : left < 0
                    ? "Over budget this month"
                    : "No days left this month"}
              </p>
            </div>
            <div
              className="h-2.5 overflow-hidden rounded-full bg-[var(--subtle)]"
              role="progressbar"
              aria-label="Budget used"
              aria-valuenow={Math.min(Math.round(usedPct), 100)}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(usedPct, 100)}%`,
                  background: usedPct > 100 ? FILL.red : usedPct >= 80 ? FILL.amber : FILL.green,
                }}
              />
            </div>
            <p className="text-xs text-[var(--muted)] tabular-nums">
              {formatAmount(used)} used of {formatAmount(planned)} planned
            </p>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <KpiCard label="Income received" value={formatAmount(s.income_minor)} icon={TrendingUp} />
        <KpiCard
          label="Spent"
          value={formatAmount(s.spent_minor)}
          icon={TrendingDown}
          upIsGood={false}
        />
        <KpiCard
          label="Saved"
          value={formatAmount(s.saved_minor)}
          icon={PiggyBank}
          hint={s.saved_minor > 0 ? `${Math.round(s.savings_rate_pct)}% of income` : undefined}
        />
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <Card id="money-attention" title="Needs attention">
          {attention.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <CheckCircle2 className="h-4 w-4 text-[var(--success)]" aria-hidden />
              Everything is on track.
            </p>
          ) : (
            <ul className="flex flex-col divide-y divide-[var(--border)]">
              {attention.slice(0, 5).map((a) => (
                <li
                  key={a.key}
                  className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 py-2.5 first:pt-0 last:pb-0"
                >
                  <span className="truncate text-sm text-[var(--ink)]">{a.text}</span>
                  <StatusChip tone={a.tone}>{a.hint}</StatusChip>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-[var(--muted)]">
            <Link
              href={`/money?tab=budgets&period=${period}`}
              className="text-[var(--accent)] hover:underline"
            >
              Mark bills paid in Budget
            </Link>
          </p>
        </Card>

        <Card id="money-top" title="Where it went" description="Top spending this month">
          {top.length === 0 ? (
            <EmptyState
              compact
              title="No spending yet"
              description="Use Add expense at the top of the page."
            />
          ) : (
            <ul className="flex flex-col gap-3.5">
              {top.map((r) => (
                <BarRow
                  key={r.category_id}
                  name={r.category}
                  figure={formatAmount(r.amount_minor)}
                  pct={(r.amount_minor / topMax) * 100}
                  color="var(--chart-1)"
                />
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card
        id="money-recent"
        title="Recent activity"
        action={
          <Link
            href={`/money?tab=transactions&period=${period}`}
            className="inline-flex min-h-11 items-center text-xs font-medium text-[var(--accent)] hover:underline"
          >
            See all
          </Link>
        }
      >
        {!recent.data || recent.data.length === 0 ? (
          <EmptyState compact title="Nothing recorded this month" />
        ) : (
          <ul className="flex flex-col divide-y divide-[var(--border)]">
            {recent.data.slice(0, 5).map((tx) => (
              <TxRow key={tx.id} tx={tx} categoryName={names.get(tx.category_id ?? "")} />
            ))}
          </ul>
        )}
      </Card>

      {months.length > 1 ? (
        <Card id="money-history" title="Month by month">
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
                    style={{
                      width: `${(m.income_minor / Math.max(1, ...months.map((x) => Math.max(x.income_minor, x.spent_minor)))) * 100}%`,
                    }}
                  />
                  <span
                    className="h-1.5 rounded-full bg-[var(--chart-4)]"
                    style={{
                      width: `${(m.spent_minor / Math.max(1, ...months.map((x) => Math.max(x.income_minor, x.spent_minor)))) * 100}%`,
                    }}
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
        </Card>
      ) : null}
    </div>
  );
}

/** Due within 3 days (or already past). */
function isSoon(iso: string): boolean {
  const due = new Date(`${iso}T00:00:00`).getTime();
  return due - Date.now() < 3 * 86_400_000;
}
