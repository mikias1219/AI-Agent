"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusChip } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import type { HabitToday } from "@/lib/api/habits";
import type { MoneyRow } from "@/lib/api/finance";
import { patchTask } from "@/lib/api/tasks";
import type { TodayPlanTask } from "@/lib/api/today";
import { formatMoney } from "@/lib/money";
import { HabitChips } from "@/features/habits/habit-chips";
import { QuickAdd } from "@/features/money/quick-add";
import { dueLabel } from "@/features/money/occurrence-list";

const LINK =
  "inline-flex min-h-11 items-center text-xs font-medium text-[var(--accent)] hover:underline";

/** One inline line inside the plan card: how many are overdue, and one action to move them. */
export function OverdueNotice({
  tasks,
  today,
  onChange,
}: {
  tasks: TodayPlanTask[];
  today: string;
  onChange: () => void;
}) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(false);
  if (tasks.length === 0 || !today) return null;

  async function moveAll() {
    setBusy(true);
    try {
      await Promise.all(tasks.map((t) => patchTask(t.id, { plan_date: today })));
      toast(`Moved ${tasks.length} task${tasks.length === 1 ? "" : "s"} to today`, "success");
      onChange();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--warning)_35%,var(--border))] bg-[color-mix(in_srgb,var(--warning)_8%,var(--surface))] px-3 py-2">
      <p className="min-w-0 text-sm text-[var(--ink)]">
        <span className="font-medium">{tasks.length} overdue</span>
        <span className="text-[var(--muted)]">
          {" "}
          ·{" "}
          {tasks
            .slice(0, 2)
            .map((t) => t.title)
            .join(", ")}
        </span>
        {tasks.length > 2 ? (
          <span className="text-[var(--muted)]"> +{tasks.length - 2}</span>
        ) : null}
      </p>
      <Button size="sm" variant="secondary" loading={busy} onClick={() => void moveAll()}>
        Move to today
      </Button>
    </div>
  );
}

export function HabitsCard({ data, onChange }: { data: HabitToday; onChange: () => void }) {
  if (data.items.length === 0) return null;
  return (
    <Card
      id="today-habits"
      title="Habits"
      description={`${data.done} of ${data.due} done`}
      action={
        <Link href="/habits" className={LINK}>
          Manage
        </Link>
      }
    >
      <HabitChips data={data} onChange={onChange} />
    </Card>
  );
}

export function MoneyCard({ data, onChange }: { data: MoneyRow; onChange: () => void }) {
  return (
    <Card
      id="today-money"
      title="Money"
      action={
        <Link href="/money" className={LINK}>
          Open Money
        </Link>
      }
    >
      <dl className="mb-4 grid grid-cols-3 gap-3 text-sm">
        <div>
          <dt className="text-xs text-[var(--muted)]">Spent today</dt>
          <dd className="font-semibold tabular-nums text-[var(--ink)]">
            {formatMoney(data.spent_today_minor, data.currency)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-[var(--muted)]">Left this month</dt>
          <dd className="font-semibold tabular-nums text-[var(--ink)]">
            {data.left_this_month_minor === null
              ? "No budget"
              : formatMoney(data.left_this_month_minor, data.currency)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-[var(--muted)]">Next bill</dt>
          <dd className="truncate font-semibold text-[var(--ink)]">
            {data.next_bill
              ? `${data.next_bill.title} ${dueLabel(data.next_bill.due_date)}`
              : "None soon"}
          </dd>
        </div>
      </dl>
      <QuickAdd compact onSaved={onChange} />
    </Card>
  );
}
