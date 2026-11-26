"use client";

import { useState } from "react";
import { PiggyBank, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { KpiCard } from "@/components/ui/kpi-card";
import { StatusChip } from "@/components/ui/status-chip";
import { getOverview, RANGES, type MoneyOverview, type RangeId } from "@/lib/api/finance";
import { formatAmount, formatMoney } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";

/** "Net 9,550 ETB" is green when positive and red when negative; the sign is always shown too. */
function Net({ minor }: { minor: number }) {
  const tone = minor >= 0 ? "text-[var(--success)]" : "text-[var(--danger)]";
  return (
    <span className={`font-semibold tabular-nums ${tone}`}>
      {minor > 0 ? "+" : ""}
      {formatMoney(minor)}
    </span>
  );
}

function Share({ name, minor, pct }: { name: string; minor: number; pct: number }) {
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1">
      <span className="truncate text-sm text-[var(--ink)]">{name}</span>
      <span className="text-right text-xs text-[var(--muted)] tabular-nums">
        {formatAmount(minor)} · {pct}%
      </span>
      <span className="col-span-2 h-1.5 overflow-hidden rounded-full bg-[var(--subtle)]">
        <span
          className="block h-full rounded-full bg-[var(--accent)]"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </span>
    </li>
  );
}

function Bars({ days }: { days: MoneyOverview["by_day"] }) {
  const max = Math.max(1, ...days.map((d) => d.spent_minor));
  return (
    <div className="flex h-24 items-end gap-1" role="img" aria-label="Spending by day">
      {days.map((d) => (
        <span
          key={d.day}
          title={`${d.day}: ${formatMoney(d.spent_minor)}`}
          className="min-w-1 flex-1 rounded-t bg-[var(--danger)] opacity-80"
          style={{ height: `${Math.max(3, (d.spent_minor / max) * 100)}%` }}
        />
      ))}
    </div>
  );
}

function Forecast({ data }: { data: NonNullable<MoneyOverview["forecast"]> }) {
  return (
    <Card id="money-forecast" title="Forecast" description={data.basis}>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        {[
          ["Expected income", data.expected_income_minor],
          ["Bills and recurring", -data.committed_minor],
          ["Usual variable spend", -data.variable_minor],
          ["Planned savings", -data.planned_savings_minor],
        ].map(([label, value]) => (
          <div key={label as string}>
            <dt className="text-xs text-[var(--muted)]">{label}</dt>
            <dd className="font-medium text-[var(--ink)] tabular-nums">
              {formatMoney(value as number)}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-sm">
        Forecast left: <Net minor={data.left_minor} />
      </p>
      {!data.has_payslip ? (
        <p className="mt-1 text-xs text-[var(--muted)]">
          No payslip yet, so expected income is only what you scheduled. Add one under Income.
        </p>
      ) : null}
      {data.below_buffer ? (
        <p role="status" className="mt-2 text-sm text-[var(--warning)]">
          Below your {formatMoney(data.buffer_minor)} safety buffer.
          {data.trim_suggestions.length
            ? ` Trim: ${data.trim_suggestions.map((t) => t.category).join(", ")}.`
            : ""}
        </p>
      ) : null}
    </Card>
  );
}

/** One switcher drives every card below it: what came in, what went out, what is left. */
export function PeriodTab() {
  const [range, setRange] = useState<RangeId>("month");
  const [custom, setCustom] = useState({ start: "", end: "" });
  const ready =
    range !== "custom" || (custom.start !== "" && custom.end >= custom.start && custom.end !== "");
  const { data, error, loading, reload } = useLoad(
    () => (ready ? getOverview(range, custom) : Promise.resolve(null)),
    [range, custom.start, custom.end],
  );

  return (
    <div className="flex flex-col gap-4">
      <div role="group" aria-label="Period" className="flex flex-wrap gap-1.5">
        {RANGES.map((r) => (
          <button
            key={r.id}
            type="button"
            aria-pressed={range === r.id}
            onClick={() => setRange(r.id)}
            className={`min-h-11 rounded-full border px-3.5 text-sm transition focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${
              range === r.id
                ? "border-[var(--accent)] bg-[var(--accent-soft)] font-medium text-[var(--accent-strong)]"
                : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--ink)]"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>
      {range === "custom" ? (
        <div className="flex flex-wrap items-center gap-2">
          <Input
            type="date"
            aria-label="From"
            value={custom.start}
            onChange={(e) => setCustom({ ...custom, start: e.target.value })}
            className="w-auto"
          />
          <span className="text-sm text-[var(--muted)]">to</span>
          <Input
            type="date"
            aria-label="To"
            value={custom.end}
            onChange={(e) => setCustom({ ...custom, end: e.target.value })}
            className="w-auto"
          />
        </div>
      ) : null}

      {!ready ? (
        <EmptyState compact title="Pick a start and end date" />
      ) : loading && !data ? (
        <CardSkeleton rows={4} />
      ) : error ? (
        <ErrorBlock what="this period" message={error} onRetry={() => void reload()} />
      ) : data ? (
        <>
          <p className="text-xs text-[var(--muted)]">
            {data.first} to {data.last}, compared with {data.previous.first} to {data.previous.last}
          </p>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <KpiCard
              label="Income"
              value={formatMoney(data.income_minor)}
              icon={TrendingUp}
              delta={data.income_change_pct}
            />
            <KpiCard
              label="Spent"
              value={formatMoney(data.spent_minor)}
              icon={TrendingDown}
              delta={data.spent_change_pct}
              upIsGood={false}
            />
            <KpiCard
              label="Saved"
              value={formatMoney(data.saved_minor)}
              icon={PiggyBank}
              delta={data.saved_change_pct}
              hint={`${data.savings_rate_pct}% of income`}
            />
            <KpiCard
              label="Left"
              value={formatMoney(data.left_minor)}
              icon={Wallet}
              hint={
                data.daily_allowance_minor !== null
                  ? `${formatMoney(data.daily_allowance_minor)} a day, ${data.days_left} days left`
                  : undefined
              }
              tone={data.pace !== null && data.pace > 1 ? "warning" : "default"}
            />
          </div>
          <p className="text-sm text-[var(--ink)]">
            Net for the range: <Net minor={data.net_minor} />
            {data.pace !== null ? (
              <StatusChip tone={data.pace > 1 ? "warning" : "success"} className="ml-2">
                Pace {data.pace.toFixed(2)}
              </StatusChip>
            ) : null}
          </p>
          {data.forecast ? <Forecast data={data.forecast} /> : null}
          {data.transaction_count === 0 && !data.forecast ? (
            <EmptyState
              compact
              title="Nothing logged in this period"
              description="Use + to add an expense or income."
            />
          ) : null}
          {data.by_day.length > 1 ? (
            <Card id="money-by-day" title="Spent by day">
              <Bars days={data.by_day} />
            </Card>
          ) : null}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {data.categories.length > 0 ? (
              <Card id="money-categories" title="Where it went">
                <ul className="flex flex-col gap-3">
                  {data.top_categories.map((c) => (
                    <Share
                      key={c.category}
                      name={c.category}
                      minor={c.amount_minor}
                      pct={c.share_pct}
                    />
                  ))}
                </ul>
              </Card>
            ) : null}
            {data.income_breakdown.length > 0 ? (
              <Card id="money-income-sources" title="Where income came from">
                <ul className="flex flex-col gap-3">
                  {data.income_breakdown.map((c) => (
                    <Share
                      key={c.source}
                      name={c.source}
                      minor={c.amount_minor}
                      pct={c.share_pct}
                    />
                  ))}
                </ul>
              </Card>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
