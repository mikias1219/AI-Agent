"use client";

import { useCallback, useEffect, useState } from "react";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Tabs } from "@/components/ui/tabs";
import { apiErrorMessage } from "@/lib/api/client";
import { listApprovals } from "@/lib/api/approvals";
import type { Approval } from "@/lib/api/types";

type Tab = "approvals" | "reminders" | "history";

export function InboxPage() {
  const [tab, setTab] = useState<Tab>("approvals");
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setApprovals(await listApprovals());
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
          Pending approvals first. Reminders arrive when the scheduler ships.
        </p>
      </header>

      <Tabs
        value={tab}
        onChange={(value) => setTab(value as Tab)}
        items={[
          { id: "approvals", label: `Needs approval (${pending.length})` },
          { id: "reminders", label: "Reminders" },
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
        <EmptyState
          title="Reminders come in P6"
          description="The scheduler will deliver due reminders here. Nothing is invented meanwhile."
        />
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
