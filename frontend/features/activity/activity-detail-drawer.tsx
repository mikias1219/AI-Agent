"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Drawer } from "@/components/ui/drawer";
import { Spinner } from "@/components/ui/spinner";
import { getRunDetail } from "@/lib/api/activity";
import { apiErrorMessage } from "@/lib/api/client";
import type { ActivityEvent, RunDetail } from "@/lib/api/types";
import { formatActivityEvent, formatActivityWhen } from "./format";

export type ActivityDetailDrawerProps = {
  event: ActivityEvent | null;
  open: boolean;
  onClose: () => void;
};

function runIdFromDetails(details: Record<string, unknown>): string | null {
  const value = details.run_id;
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function ActivityDetailDrawer({ event, open, onClose }: ActivityDetailDrawerProps) {
  const runId = event ? runIdFromDetails(event.details) : null;
  const [run, setRun] = useState<RunDetail | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !runId) {
      setRun(null);
      setRunError(null);
      setRunLoading(false);
      return;
    }
    let cancelled = false;
    setRunLoading(true);
    setRunError(null);
    getRunDetail(runId)
      .then((detail) => {
        if (!cancelled) setRun(detail);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setRun(null);
          setRunError(apiErrorMessage(err));
        }
      })
      .finally(() => {
        if (!cancelled) setRunLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, runId]);

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={event ? formatActivityEvent(event.event) : "Activity"}
    >
      {event ? (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">{event.actor}</Badge>
            <time className="text-xs text-[var(--muted)]" dateTime={event.occurred_at}>
              {formatActivityWhen(event.occurred_at)}
            </time>
          </div>
          <dl className="grid grid-cols-[5.5rem_1fr] gap-x-3 gap-y-2 text-sm">
            <dt className="text-[var(--muted)]">Event</dt>
            <dd className="text-[var(--ink)]">{event.event}</dd>
            <dt className="text-[var(--muted)]">Id</dt>
            <dd className="text-[var(--ink)]">{event.id}</dd>
            {runId ? (
              <>
                <dt className="text-[var(--muted)]">Run</dt>
                <dd className="font-mono text-xs text-[var(--ink)]">{runId}</dd>
              </>
            ) : null}
          </dl>
          <div>
            <h3 className="text-sm font-medium text-[var(--ink)]">Details</h3>
            <pre className="mt-2 overflow-auto rounded-[var(--radius)] bg-[var(--canvas)] p-3 text-xs whitespace-pre-wrap text-[var(--ink)]">
              {formatDetails(event.details)}
            </pre>
          </div>
          {runId ? (
            <div>
              <h3 className="text-sm font-medium text-[var(--ink)]">Run detail</h3>
              {runLoading ? (
                <div className="mt-2 flex items-center gap-2 text-sm text-[var(--muted)]">
                  <Spinner size="sm" />
                  Loading steps…
                </div>
              ) : null}
              {runError ? (
                <p className="mt-2 text-sm text-[var(--danger)]" role="alert">
                  {runError}
                </p>
              ) : null}
              {run && !runLoading ? (
                <div className="mt-2 flex flex-col gap-3 text-sm">
                  <dl className="grid grid-cols-[5.5rem_1fr] gap-x-3 gap-y-2">
                    <dt className="text-[var(--muted)]">Status</dt>
                    <dd>{run.status}</dd>
                    <dt className="text-[var(--muted)]">Model</dt>
                    <dd>{run.model || "—"}</dd>
                    <dt className="text-[var(--muted)]">Trace</dt>
                    <dd className="font-mono text-xs break-all">{run.trace_id || "—"}</dd>
                    <dt className="text-[var(--muted)]">Latency</dt>
                    <dd>{run.latency_ms != null ? `${run.latency_ms} ms` : "—"}</dd>
                    <dt className="text-[var(--muted)]">Tokens</dt>
                    <dd>
                      {run.input_tokens != null || run.output_tokens != null
                        ? `${run.input_tokens ?? "—"} in / ${run.output_tokens ?? "—"} out`
                        : "—"}
                    </dd>
                  </dl>
                  {run.steps.length === 0 ? (
                    <p className="text-[var(--muted)]">No tool steps for this run.</p>
                  ) : (
                    <ol className="flex flex-col gap-2">
                      {run.steps.map((step) => (
                        <li
                          key={step.id}
                          className="rounded-[var(--radius)] border border-[var(--border)] px-3 py-2"
                        >
                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <span className="font-medium text-[var(--ink)]">
                              {step.seq}. {step.name}
                            </span>
                            <span className="text-xs text-[var(--muted)]">
                              {step.status}
                              {step.duration_ms != null ? ` · ${step.duration_ms} ms` : ""}
                            </span>
                          </div>
                          {step.output ? (
                            <p className="mt-1 text-xs text-[var(--muted)] line-clamp-3">
                              {step.output}
                            </p>
                          ) : null}
                          {step.error ? (
                            <p className="mt-1 text-xs text-[var(--danger)]">{step.error}</p>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </Drawer>
  );
}

function formatDetails(details: Record<string, unknown>): string {
  try {
    return JSON.stringify(details, null, 2);
  } catch {
    return "Details could not be displayed.";
  }
}
