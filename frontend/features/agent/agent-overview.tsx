"use client";

import { formatDateTime } from "@/lib/format-date";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { SkeletonRows } from "@/components/ui/skeleton";
import { StatusChip } from "@/components/ui/status-chip";
import { apiErrorMessage } from "@/lib/api/client";
import {
  AUTONOMY_LABELS,
  AUTONOMY_TODAY,
  getAgentControl,
  patchAgentControl,
  type AgentControlState,
} from "@/lib/api/agent-control";
import { getAgentCapabilities, type AgentCapabilities } from "@/lib/api/agent-capabilities";
import { listAgentSkills, type AgentSkill } from "@/lib/api/agent-skills";
import { listActivity } from "@/lib/api/activity";
import { getStatus } from "@/lib/api/status";
import { TrustReport } from "./trust-report";
import type { ActivityEvent, StatusPayload } from "@/lib/api/types";

const ACCESS_LABEL: Record<string, string> = {
  read: "Read",
  prepare: "Prepare",
  execute: "Commit",
  financial: "Money",
  destructive: "Delete",
};

export function AgentOverview() {
  const [control, setControl] = useState<AgentControlState | null>(null);
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [capabilities, setCapabilities] = useState<AgentCapabilities | null>(null);
  const [skills, setSkills] = useState<AgentSkill[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextControl, nextStatus, nextCaps, nextSkills, nextActivity] = await Promise.all([
        getAgentControl(),
        getStatus(),
        getAgentCapabilities(),
        listAgentSkills().catch(() => [] as AgentSkill[]),
        listActivity({ limit: 8 }).catch(() => [] as ActivityEvent[]),
      ]);
      setControl(nextControl);
      setStatus(nextStatus);
      setCapabilities(nextCaps);
      setSkills(nextSkills);
      setActivity(nextActivity);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function togglePause() {
    if (!control) return;
    setBusy(true);
    try {
      setControl(await patchAgentControl({ paused: !control.paused }));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading && !control) {
    return <SkeletonRows count={4} />;
  }

  if (error && !control) {
    return (
      <Banner tone="danger" role="alert">
        {error}{" "}
        <Button size="sm" variant="secondary" onClick={() => void load()}>
          Try again
        </Button>
      </Banner>
    );
  }

  const commits = control?.budgets;
  const counts = capabilities?.counts ?? {};

  return (
    <div className="flex flex-col gap-5">
      {error ? (
        <Banner tone="danger" role="alert">
          {error}
        </Banner>
      ) : null}

      <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-[length:var(--text-title)] font-semibold text-[var(--ink)]">
              Status
            </h2>
            <p className="mt-1 text-[length:var(--text-small)] text-[var(--muted)]">
              Runtime {status?.active_runtime ?? "unknown"}
              {status?.model ? ` · ${status.model}` : ""}
            </p>
          </div>
          {control ? (
            <StatusChip tone={control.paused ? "warning" : "success"}>
              {control.paused ? "Paused" : "Listening"}
            </StatusChip>
          ) : null}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant={control?.paused ? "primary" : "secondary"}
            loading={busy}
            onClick={() => void togglePause()}
          >
            {control?.paused ? "Resume agent" : "Pause agent"}
          </Button>
          <p className="text-[length:var(--text-small)] text-[var(--muted)]">
            Autonomy: {control ? AUTONOMY_LABELS[control.autonomy_preset] : "—"}
          </p>
        </div>
        <p className="mt-3 text-[length:var(--text-caption)] text-[var(--muted)]">
          {AUTONOMY_TODAY}
        </p>
      </section>

      <TrustReport />

      <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4">
        <h2 className="text-[length:var(--text-title)] font-semibold text-[var(--ink)]">
          Today&apos;s limits
        </h2>
        <ul className="mt-3 flex flex-col gap-2 text-[length:var(--text-body)] text-[var(--ink)]">
          <li>
            Approved commits: {commits?.commits_used ?? 0} of {commits?.commits_cap ?? 20}
            <span className="text-[var(--muted)]">
              {" "}
              (sends, calendar changes and deletes after you approve)
            </span>
          </li>
          <li>
            Scheduled messages: {commits?.proactive_used ?? 0} of {commits?.proactive_cap ?? 3}
          </li>
        </ul>
        <p className="mt-2 text-[length:var(--text-small)] text-[var(--muted)]">
          Change the autonomy preference in{" "}
          <Link
            href="/settings?section=permissions"
            className="text-[var(--accent)] hover:underline"
          >
            Settings
          </Link>
          .
        </p>
      </section>

      <details className="group rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4">
        <summary className="flex min-h-11 cursor-pointer items-center justify-between text-[length:var(--text-title)] font-semibold text-[var(--ink)]">
          Technical details
          <span className="text-xs font-normal text-[var(--muted)]">Capabilities and tools</span>
        </summary>
        <h2 className="mt-3 text-[length:var(--text-body)] font-semibold text-[var(--ink)]">
          Capabilities
        </h2>
        <p className="mt-1 text-[length:var(--text-small)] text-[var(--muted)]">
          From the live tool registry. Commit, money and delete tools always ask first.
        </p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {(["read", "prepare", "execute", "financial", "destructive"] as const).map((kind) => (
            <li key={kind}>
              <StatusChip tone={kind === "read" || kind === "prepare" ? "neutral" : "warning"}>
                {ACCESS_LABEL[kind] ?? kind}: {counts[kind] ?? 0}
              </StatusChip>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[length:var(--text-small)] text-[var(--muted)]">
          {skills.length} shipped playbook{skills.length === 1 ? "" : "s"}. See Memory → Playbooks.
        </p>
      </details>

      <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[length:var(--text-title)] font-semibold text-[var(--ink)]">
            Recent activity
          </h2>
          <Link
            href="/activity"
            className="text-[length:var(--text-small)] text-[var(--accent)] hover:underline"
          >
            Open Activity
          </Link>
        </div>
        {activity.length === 0 ? (
          <p className="mt-3 text-[length:var(--text-body)] text-[var(--muted)]">
            Nothing recorded yet.
          </p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {activity.map((row) => (
              <li
                key={row.id}
                className="flex flex-wrap items-baseline justify-between gap-2 text-[length:var(--text-body)]"
              >
                <span className="text-[var(--ink)]">{row.event}</span>
                <time
                  className="text-[length:var(--text-caption)] text-[var(--muted)]"
                  dateTime={row.occurred_at}
                >
                  {formatDateTime(row.occurred_at)}
                </time>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
