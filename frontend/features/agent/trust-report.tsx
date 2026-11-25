"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Gavel, OctagonAlert, PlayCircle } from "lucide-react";
import { DonutChart } from "@/components/charts/donut-chart";
import { StackedBarChart } from "@/components/charts/stacked-bar-chart";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { listRecentActivity } from "@/lib/api/activity";
import { apiErrorMessage } from "@/lib/api/client";
import type { ActivityEvent } from "@/lib/api/types";
import { ACTIVITY_SERIES, breakdown, bucketByDay, sum } from "@/lib/dashboard-stats";

const DAYS = 14;

const COLOR = Object.fromEntries(ACTIVITY_SERIES.map((s) => [s.key, s.color]));

/** Real numbers from the audit log: what AURA did, how often it worked, and how often you decided. */
export function TrustReport() {
  const [events, setEvents] = useState<ActivityEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    listRecentActivity()
      .then(setEvents)
      .catch((err: unknown) => setError(apiErrorMessage(err)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const buckets = useMemo(() => (events ? bucketByDay(events, DAYS) : null), [events]);
  const totals = useMemo(() => {
    const out = { completed: 0, failed: 0, approvals: 0, total: 0 };
    for (const b of buckets ?? []) {
      out.completed += b.counts.completed ?? 0;
      out.failed += b.counts.failed ?? 0;
      out.approvals += b.counts.approvals ?? 0;
      out.total += b.total;
    }
    return out;
  }, [buckets]);
  const slices = useMemo(
    () =>
      buckets
        ? breakdown(buckets).map((b) => ({ ...b, color: COLOR[b.key] ?? "var(--chart-5)" }))
        : [],
    [buckets],
  );

  const finished = totals.completed + totals.failed;
  const successRate = finished > 0 ? Math.round((totals.completed / finished) * 100) : null;

  return (
    <section aria-labelledby="trust-report" className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2
            id="trust-report"
            className="text-[length:var(--text-title)] font-semibold text-[var(--ink)]"
          >
            Trust report
          </h2>
          <p className="text-[length:var(--text-small)] text-[var(--muted)]">
            From the audit log, last {DAYS} days. Nothing here is estimated.
          </p>
        </div>
      </div>

      {error ? (
        <div className="flex flex-wrap items-center gap-3 text-sm" role="alert">
          <span className="text-[var(--danger)]">Could not load the audit log: {error}</span>
          <Button size="sm" variant="secondary" onClick={load}>
            Try again
          </Button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Runs finished"
              value={buckets ? totals.completed : "—"}
              icon={PlayCircle}
              href="/activity"
            />
            <KpiCard
              label="Success rate"
              value={successRate === null ? "—" : `${successRate}%`}
              icon={CheckCircle2}
              hint={successRate === null ? "No finished runs yet" : `${finished} runs counted`}
            />
            <KpiCard
              label="Approvals decided"
              value={buckets ? totals.approvals : "—"}
              icon={Gavel}
              href="/inbox"
            />
            <KpiCard
              label="Failed or stopped"
              value={buckets ? totals.failed : "—"}
              icon={OctagonAlert}
              tone={totals.failed > 0 ? "warning" : "default"}
              hint={totals.failed > 0 ? "Open Activity to see why" : undefined}
              href="/activity"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
            <Card id="trust-daily" title="Actions per day" description={`Last ${DAYS} days`}>
              {!buckets ? (
                <div
                  className="h-48 animate-pulse rounded-[var(--radius)] bg-[var(--subtle)]"
                  role="status"
                  aria-label="Loading"
                />
              ) : sum(buckets.map((b) => b.total)) === 0 ? (
                <p className="text-sm text-[var(--muted)]">No recorded activity yet.</p>
              ) : (
                <StackedBarChart
                  data={buckets.slice(-7)}
                  series={ACTIVITY_SERIES}
                  label="AURA actions per day, last 7 days"
                />
              )}
            </Card>
            <Card id="trust-mix" title="Mix of actions" description={`Last ${DAYS} days`}>
              {!buckets ? (
                <div className="h-32 animate-pulse rounded-[var(--radius)] bg-[var(--subtle)]" />
              ) : slices.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">Nothing to show yet.</p>
              ) : (
                <DonutChart
                  slices={slices}
                  label="Share of AURA actions by type"
                  centerLabel="actions"
                />
              )}
            </Card>
          </div>
        </>
      )}
    </section>
  );
}
