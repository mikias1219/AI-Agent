import type { BudgetAlert, MoneyInsightItem, Occurrence } from "@/lib/api/finance";
import { formatMoney } from "@/lib/money";

/**
 * The one line each agent bar shows, picked from real data in a fixed order of urgency.
 * Pure so the choice is unit tested; pages fetch and pass the rows in.
 */

export function moneyInsight(
  budget: readonly BudgetAlert[],
  due: readonly Occurrence[],
  insights: readonly MoneyInsightItem[],
): string | null {
  const over = budget.find((b) => b.status === "red");
  if (over) return `${over.category} is over budget with ${dayWord(over.days_left)} left.`;
  const overdue = due.find((o) => o.kind === "bill" && o.status === "overdue");
  if (overdue) return `${overdue.title} is overdue: ${formatMoney(overdue.remaining_minor)}.`;
  const warn = insights.find((i) => i.severity === "warning");
  if (warn) return warn.message;
  const near = budget.find((b) => b.status === "amber");
  if (near) {
    return `${near.category} is at ${Math.round(near.utilisation_pct)}% of budget with ${dayWord(near.days_left)} left.`;
  }
  const bill = due.find((o) => o.kind === "bill");
  if (bill) return `${bill.title} is due ${bill.due_date}: ${formatMoney(bill.remaining_minor)}.`;
  const income = due.find((o) => o.kind === "income");
  if (income) return `${income.title} is expected today. Did it arrive?`;
  return insights[0]?.message ?? null;
}

export function planInsight(open: number | null | undefined, unscheduled: number): string | null {
  if (open == null) return null;
  if (open === 0) return "Everything planned for today is done.";
  if (unscheduled > 0) {
    return `${open} ${open === 1 ? "task" : "tasks"} left today, ${unscheduled} without a time.`;
  }
  return `${open} ${open === 1 ? "task" : "tasks"} left today.`;
}

function dayWord(days: number): string {
  return days === 1 ? "1 day" : `${Math.max(days, 0)} days`;
}

type TodayLike = {
  needs_you?: readonly unknown[];
  plan?: { tasks?: readonly { due_at: string | null; status: string }[] };
  day?: { summary?: { open?: number } } | null;
} | null;

/** Today's bar: approvals first, then tasks without a time, then what is left. */
export function todayInsight(today: TodayLike): string | null {
  if (!today) return null;
  const waiting = today.needs_you?.length ?? 0;
  if (waiting > 0) {
    return `${waiting} ${waiting === 1 ? "item needs" : "items need"} your approval.`;
  }
  const open = (today.plan?.tasks ?? []).filter((t) => t.status !== "done");
  const untimed = open.filter((t) => !t.due_at).length;
  if (untimed > 0) {
    return `${untimed} ${untimed === 1 ? "task has" : "tasks have"} no time yet — I can fit them into your free blocks.`;
  }
  return planInsight(today.day?.summary?.open ?? null, 0);
}
