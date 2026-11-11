"use client";

import { useState } from "react";
import { Check, ChevronDown, ChevronRight, X } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { formatDuration, stepLabel, trailSummary, type TrailStep } from "./run-trail";

const approvalText: Record<NonNullable<TrailStep["approval"]>, string> = {
  waiting: "Waiting for your approval",
  approved: "Approved",
  denied: "Denied",
  deferred: "Needs approval in Approvals",
};

/** Collapsible list of what the agent did for one answer. Open while it works. */
export function StepTrail({ steps, pending }: { steps: TrailStep[]; pending: boolean }) {
  const [manual, setManual] = useState<boolean | null>(null);
  if (steps.length === 0) return null;
  const open = manual ?? pending;
  const listId = `trail-${steps[0].id}`;

  return (
    <div className="mb-2 text-xs text-[var(--muted)]">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setManual(!open)}
        className="inline-flex items-center gap-1 rounded-[var(--radius)] py-1 font-medium hover:text-[var(--ink)]"
      >
        {open ? (
          <ChevronDown className="size-3.5" aria-hidden />
        ) : (
          <ChevronRight className="size-3.5" aria-hidden />
        )}
        {trailSummary(steps, pending)}
      </button>
      {open ? (
        <ol id={listId} className="mt-1 flex flex-col gap-1 border-l border-[var(--border)] pl-3">
          {steps.map((step) => (
            <li key={step.id} className="flex flex-wrap items-center gap-x-2">
              {step.status === "running" ? (
                <Spinner size="sm" />
              ) : step.status === "ok" ? (
                <Check className="size-3.5 text-[var(--accent)]" aria-label="Done" />
              ) : (
                <X className="size-3.5 text-[var(--danger)]" aria-label="Failed" />
              )}
              <span className="text-[var(--ink)]">{stepLabel(step.name)}</span>
              {step.durationMs !== undefined ? (
                <span>{formatDuration(step.durationMs)}</span>
              ) : null}
              {step.approval ? <span role="status">{approvalText[step.approval]}</span> : null}
              {step.status === "failed" && step.detail ? (
                <span className="basis-full text-[var(--danger)]">{step.detail}</span>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
