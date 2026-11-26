"use client";

import { useState } from "react";
import { ClipboardCheck } from "lucide-react";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { KpiCard } from "@/components/ui/kpi-card";
import { Tabs } from "@/components/ui/tabs";
import { formatMinutes } from "@/lib/api/time";
import { getReview, type ReviewPeriod } from "@/lib/api/review";
import { formatDate } from "@/lib/format-date";
import { formatMoney } from "@/lib/money";
import { percentChange } from "@/lib/dashboard-stats";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";
import { CheckCircle2, Repeat, Wallet } from "lucide-react";

const PERIODS = [
  { id: "week", label: "This week" },
  { id: "month", label: "Last 30 days" },
];

const pct = (value: number | null) => (value === null ? "No data" : `${Math.round(value * 100)}%`);

/** Am I improving? One page for tasks, habits and money over the last week or month. */
export function ReviewPage({ embedded = false }: { embedded?: boolean }) {
  void embedded;
  const [period, setPeriod] = useState<ReviewPeriod>("week");
  const review = useLoad(() => getReview(period), [period]);

  const body = () => {
    if (review.error)
      return (
        <ErrorBlock what="the review" message={review.error} onRetry={() => void review.reload()} />
      );
    if (!review.data) return <CardSkeleton rows={5} />;
    const r = review.data;
    if (r.tasks.planned === 0 && r.habits.length === 0 && r.money.spent_minor === 0) {
      return (
        <EmptyState
          icon={ClipboardCheck}
          title="Nothing to review yet"
          description="Plan a few tasks, add a habit or record spending, and your review fills in."
        />
      );
    }
    const delta =
      r.tasks.rate !== null && r.tasks.previous_rate !== null
        ? percentChange(Math.round(r.tasks.rate * 100), Math.round(r.tasks.previous_rate * 100))
        : null;
    return (
      <div className="flex flex-col gap-5">
        <p className="text-sm text-[var(--muted)]">
          {formatDate(r.from)} to {formatDate(r.to)}
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <KpiCard
            label="Tasks finished"
            value={pct(r.tasks.rate)}
            icon={CheckCircle2}
            delta={delta}
            hint={`${r.tasks.achieved + r.tasks.partial} of ${r.tasks.planned} planned`}
          />
          <KpiCard
            label="Habits done"
            value={pct(
              r.habits.reduce((n, h) => n + h.due, 0)
                ? r.habits.reduce((n, h) => n + h.done, 0) / r.habits.reduce((n, h) => n + h.due, 0)
                : null,
            )}
            icon={Repeat}
            hint={`${r.habits.length} habit${r.habits.length === 1 ? "" : "s"}`}
          />
          <KpiCard
            label="Spent"
            value={formatMoney(r.money.spent_minor)}
            icon={Wallet}
            upIsGood={false}
            delta={
              r.money.previous_spent_minor
                ? percentChange(r.money.spent_minor, r.money.previous_spent_minor)
                : null
            }
            hint={`Saved ${formatMoney(r.money.saved_minor)}`}
          />
        </div>

        {r.highlights.length > 0 ? (
          <Card id="review-highlights" title="What stands out">
            <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm text-[var(--ink)]">
              {r.highlights.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Card>
        ) : null}

        {r.time && r.time.total_minutes > 0 ? (
          <Card
            id="review-time"
            title="Where your time went"
            description={`${formatMinutes(r.time.total_minutes)} tracked`}
          >
            <ul className="flex flex-col gap-2">
              {r.time.by_project.slice(0, 5).map((row) => (
                <li key={row.project} className="flex justify-between text-sm">
                  <span className="text-[var(--ink)]">{row.project}</span>
                  <span className="text-xs text-[var(--muted)] tabular-nums">
                    {formatMinutes(row.minutes)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        ) : null}

        {r.habits.length > 0 ? (
          <Card id="review-habits" title="Habits">
            <ul className="flex flex-col gap-3">
              {r.habits.map((h) => (
                <li key={h.habit} className="flex flex-col gap-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--ink)]">{h.habit}</span>
                    <span className="text-xs text-[var(--muted)] tabular-nums">
                      {h.done}/{h.due}
                      {h.skipped ? ` · ${h.skipped} skipped` : ""}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-[var(--subtle)]">
                    <div
                      className="h-full rounded-full bg-[var(--accent)]"
                      style={{ width: `${(h.rate ?? 0) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        ) : null}

        {r.tasks.missed_tasks.length > 0 ? (
          <Card id="review-missed" title="Why things were missed" description="Your own notes.">
            <ul className="flex flex-col divide-y divide-[var(--border)]">
              {r.tasks.missed_tasks.map((t) => (
                <li key={t.id} className="py-2.5 text-sm first:pt-0 last:pb-0">
                  <p className="font-medium text-[var(--ink)]">{t.title}</p>
                  <p className="text-xs text-[var(--muted)]">
                    {formatDate(t.day)} · {t.outcome}
                    {t.note ? ` · ${t.note}` : " · no reason noted"}
                  </p>
                </li>
              ))}
            </ul>
          </Card>
        ) : null}
      </div>
    );
  };

  return (
    <Tabs
      aria-label="Review period"
      items={PERIODS}
      value={period}
      onChange={(id) => setPeriod(id as ReviewPeriod)}
      panels={{ [period]: body() }}
    />
  );
}
