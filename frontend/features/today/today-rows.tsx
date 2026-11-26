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

/** Overdue work from earlier days, with one action to bring it to today. */
export function OverdueCard({
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
    <Card
      id="today-overdue"
      title={`Overdue (${tasks.length})`}
      description="Open from earlier days."
      action={
        <Link href="/tasks" className={LINK}>
          Open Plan
        </Link>
      }
    >
      <ul className="mb-3 flex flex-col gap-2">
        {tasks.slice(0, 5).map((task) => (
          <li
            key={task.id}
            className="flex min-h-11 items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] px-3 py-2"
          >
            <span className="min-w-0 flex-1 truncate text-sm font-medium text-[var(--ink)]">
              {task.title}
            </span>
            {task.priority === "p1" ? <StatusChip tone="danger">P1</StatusChip> : null}
            <span className="text-xs text-[var(--muted)]">
              {task.plan_date ? dueLabel(task.plan_date) : ""}
            </span>
          </li>
        ))}
        {tasks.length > 5 ? (
          <li className="text-xs text-[var(--muted)]">and {tasks.length - 5} more in Plan</li>
        ) : null}
      </ul>
      <Button size="sm" variant="secondary" loading={busy} onClick={() => void moveAll()}>
        Move all to today
      </Button>
    </Card>
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
      <QuickAdd onSaved={onChange} />
    </Card>
  );
}
