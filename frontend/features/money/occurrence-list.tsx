"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { StatusChip } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { settleOccurrence, type Occurrence } from "@/lib/api/finance";
import { formatMoney } from "@/lib/money";

const TONE = {
  overdue: "danger",
  partial: "warning",
  expected: "neutral",
  paid: "success",
  skipped: "neutral",
} as const;

export function dueLabel(iso: string, today: Date = new Date()): string {
  const due = new Date(`${iso}T00:00:00`);
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((due.getTime() - start.getTime()) / 86_400_000);
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "yesterday";
  if (days < 0) return `${-days} days ago`;
  return days < 14
    ? `in ${days} days`
    : due.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Upcoming bills and income with one-tap settle. Shared by Overview and Bills & income. */
export function OccurrenceList({ items, onChange }: { items: Occurrence[]; onChange: () => void }) {
  const { toast } = useToast();
  const [busy, setBusy] = useState<string | null>(null);

  async function settle(item: Occurrence, status: "paid" | "skipped") {
    setBusy(item.id);
    try {
      await settleOccurrence(item.id, { status });
      toast(
        status === "paid"
          ? item.kind === "income"
            ? "Marked received"
            : "Marked paid"
          : "Skipped",
      );
      onChange();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(null);
    }
  }

  return (
    <ul className="flex flex-col divide-y divide-[var(--border)]">
      {items.map((item) => {
        const open = ["expected", "overdue", "partial"].includes(item.status);
        return (
          <li key={item.id} className="flex flex-wrap items-center gap-3 py-3 first:pt-0 last:pb-0">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-[var(--ink)]">{item.title}</p>
              <p className="text-xs text-[var(--muted)]">
                {item.kind === "income" ? "Expected" : "Due"} {dueLabel(item.due_date)} ·{" "}
                {formatMoney(open ? item.remaining_minor : item.expected_minor)}
              </p>
            </div>
            {item.status !== "expected" ? (
              <StatusChip tone={TONE[item.status]}>{item.status}</StatusChip>
            ) : null}
            {open ? (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  loading={busy === item.id}
                  onClick={() => void settle(item, "paid")}
                >
                  {item.kind === "income" ? "Mark received" : "Mark paid"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy === item.id}
                  onClick={() => void settle(item, "skipped")}
                >
                  Skip
                </Button>
              </div>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
