"use client";

import { useCallback, useEffect, useState } from "react";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Tabs } from "@/components/ui/tabs";
import { apiErrorMessage } from "@/lib/api/client";
import { listApprovals } from "@/lib/api/approvals";
import { listReminders, type Reminder } from "@/lib/api/automations";
import type { Approval } from "@/lib/api/types";

type Tab = "approvals" | "reminders" | "history";

export function InboxPage() {
  const [tab, setTab] = useState<Tab>("approvals");
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextApprovals, nextReminders] = await Promise.all([
        listApprovals(),
        listReminders().catch(() => [] as Reminder[]),
      ]);
      setApprovals(nextApprovals);
      setReminders(nextReminders);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const pending = approvals.filter((row) => row.actionable);
  const history = approvals.filter((row) => !row.actionable);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Inbox</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Decide quickly
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Pending approvals first. Reminders list what the scheduler delivered or still owes.
        </p>
      </header>

      <Tabs
        value={tab}
        onChange={(value) => setTab(value as Tab)}
        items={[
          { id: "approvals", label: `Needs approval (${pending.length})` },
          { id: "reminders", label: `Reminders (${reminders.length})` },
          { id: "history", label: "History" },
        ]}
      />

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Spinner size="sm" /> Loading inbox…
        </div>
      ) : null}

      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}{" "}
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Retry
          </Button>
        </p>
      ) : null}

      {!loading && tab === "approvals" ? (
        pending.length === 0 ? (
          <EmptyState
            title="No pending approvals"
            description="When AURA needs a send or change, cards appear here and on Today."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {pending.map((approval) => (
              <li key={approval.id}>
                <ApprovalCard approval={approval} onDecided={() => void load()} />
              </li>
            ))}
          </ul>
        )
      ) : null}

      {!loading && tab === "reminders" ? (
        reminders.length === 0 ? (
          <EmptyState
            title="No reminders yet"
            description="Ask AURA to remind you, or wait for scheduled deliveries. Late ones are labeled."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {reminders.map((reminder) => (
              <li
                key={reminder.id}
                className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-sm text-[var(--ink)]">{reminder.text}</p>
                  <div className="flex flex-wrap gap-1">
                    <Badge tone={reminder.status === "sent" ? "success" : "neutral"}>
                      {reminder.status}
                    </Badge>
                    {reminder.late ? <Badge tone="warning">late</Badge> : null}
                  </div>
                </div>
                <p className="mt-2 text-xs text-[var(--muted)]">
                  {reminder.remind_at
                    ? `Due ${new Date(reminder.remind_at).toLocaleString()}`
                    : "No due time"}
                  {reminder.delivered_at
                    ? ` · Delivered ${new Date(reminder.delivered_at).toLocaleString()}`
                    : ""}
                </p>
              </li>
            ))}
          </ul>
        )
      ) : null}

      {!loading && tab === "history" ? (
        history.length === 0 ? (
          <EmptyState title="No history yet" description="Past decisions will list here." />
        ) : (
          <ul className="flex flex-col gap-3">
            {history.map((approval) => (
              <li key={approval.id}>
                <ApprovalCard approval={approval} onDecided={() => void load()} />
              </li>
            ))}
          </ul>
        )
      ) : null}
    </div>
  );
}
