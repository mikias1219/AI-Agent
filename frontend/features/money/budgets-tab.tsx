"use client";

import { FormEvent, useState } from "react";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { StatusChip } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  copyBudget,
  deleteBudget,
  createBudget,
  getCategories,
  listBudgets,
  putBudgetLines,
  type Budget,
} from "@/lib/api/finance";
import { budgetTone, formatMoney, parseAmount, periodLabel, shiftPeriod } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";

/** Plan one month: income, then an amount per category. Unallocated money updates live. */
function BudgetEditor({
  period,
  budget,
  onSaved,
}: {
  period: string;
  budget: Budget | null;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const categories = useLoad(getCategories);
  const expense = (categories.data ?? []).filter((c) => c.kind === "expense");
  const [income, setIncome] = useState(budget ? String(budget.income_plan_minor / 100 || "") : "");
  const [amounts, setAmounts] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      (budget?.lines ?? []).map((l) => [l.category_id, String(l.planned_minor / 100)]),
    ),
  );
  const [busy, setBusy] = useState(false);

  const planned = Object.values(amounts).reduce((n, v) => n + (parseAmount(v) ?? 0), 0);
  const incomeValue = parseAmount(income) ?? 0;
  const unallocated = incomeValue - planned;

  async function save(event: FormEvent) {
    event.preventDefault();
    const lines = expense
      .map((c) => ({ category_id: c.id, planned: parseAmount(amounts[c.id] ?? "") ?? 0 }))
      .filter((l) => l.planned > 0);
    setBusy(true);
    try {
      if (budget) await putBudgetLines(budget.id, lines);
      else await createBudget({ period, income_plan: incomeValue || undefined, lines });
      toast("Budget saved");
      onSaved();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-4">
      {!budget ? (
        <Field label="Expected income this month" htmlFor="budget-income">
          <Input
            id="budget-income"
            inputMode="decimal"
            className="min-h-11"
            value={income}
            onChange={(e) => setIncome(e.target.value)}
            placeholder="35000"
          />
        </Field>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2">
        {expense.map((c) => (
          <Field key={c.id} label={c.name} htmlFor={`b-${c.id}`}>
            <Input
              id={`b-${c.id}`}
              inputMode="decimal"
              className="min-h-11"
              placeholder="0"
              value={amounts[c.id] ?? ""}
              onChange={(e) => setAmounts({ ...amounts, [c.id]: e.target.value })}
            />
          </Field>
        ))}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-[var(--muted)]" role="status">
          Planned {formatMoney(Math.round(planned * 100))}
          {incomeValue || budget?.income_plan_minor
            ? ` · ${unallocated >= 0 ? "unallocated" : "over by"} ${formatMoney(Math.abs(Math.round((budget ? budget.income_plan_minor / 100 - planned : unallocated) * 100)))}`
            : ""}
        </p>
        <Button type="submit" loading={busy} className="min-h-11">
          Save budget
        </Button>
      </div>
    </form>
  );
}

export function BudgetsTab({ period }: { period: string }) {
  const { toast } = useToast();
  const budgets = useLoad(listBudgets);
  const [editing, setEditing] = useState(false);

  if (budgets.error)
    return (
      <ErrorBlock what="budgets" message={budgets.error} onRetry={() => void budgets.reload()} />
    );
  if (!budgets.data) return <CardSkeleton rows={4} />;

  const current =
    budgets.data.find((b) => b.type === "monthly" && b.period_start === `${period}-01`) ?? null;
  const previous = budgets.data.find(
    (b) => b.type === "monthly" && b.period_start === `${shiftPeriod(period, -1)}-01`,
  );

  async function copyLast() {
    if (!previous) return;
    try {
      await copyBudget(previous.id, period);
      toast("Copied last month's budget");
      void budgets.reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  async function removeBudget(id: string) {
    if (!window.confirm(`Delete the budget for ${periodLabel(period)}? This cannot be undone.`))
      return;
    try {
      await deleteBudget(id);
      toast("Budget deleted.");
      void budgets.reload();
      window.dispatchEvent(new Event("compass:data-changed"));
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  if (!current) {
    return (
      <Card id="budget-new" title={`Budget for ${periodLabel(period)}`}>
        <div className="mb-4 flex flex-wrap gap-2">
          {previous ? (
            <Button variant="secondary" className="min-h-11" onClick={() => void copyLast()}>
              <Copy className="h-4 w-4" aria-hidden />
              Copy last month
            </Button>
          ) : null}
        </div>
        <BudgetEditor period={period} budget={null} onSaved={() => void budgets.reload()} />
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <Card
        id="budget-current"
        title="Spending limits"
        description={`${formatMoney(current.actual_minor)} spent of ${formatMoney(current.planned_minor)} planned`}
        action={
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => setEditing(!editing)}>
              {editing ? "Close" : "Edit amounts"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => void removeBudget(current.id)}>
              Delete
            </Button>
          </div>
        }
      >
        {editing ? (
          <BudgetEditor
            period={period}
            budget={current}
            onSaved={() => {
              setEditing(false);
              void budgets.reload();
            }}
          />
        ) : current.lines.length === 0 ? (
          <EmptyState
            compact
            title="No category amounts yet"
            description="Choose Edit amounts to plan each category."
          />
        ) : (
          <ul className="flex flex-col divide-y divide-[var(--border)]">
            {current.lines.map((l) => (
              <li
                key={l.category_id}
                className="grid grid-cols-[minmax(0,1fr)_7.5rem_3.5rem] items-center gap-x-3 py-2.5 text-sm first:pt-0 last:pb-0"
              >
                <span className="truncate text-[var(--ink)]">{l.category}</span>
                <span className="text-right text-xs text-[var(--muted)] tabular-nums">
                  {l.remaining_minor >= 0
                    ? `${formatMoney(l.remaining_minor)} left`
                    : `${formatMoney(-l.remaining_minor)} over`}
                </span>
                <span className="justify-self-end">
                  <StatusChip tone={budgetTone(l.status)}>
                    {Math.round(l.utilisation_pct)}%
                  </StatusChip>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {current.unallocated_minor !== 0 && current.income_plan_minor > 0 ? (
        <p className="text-sm text-[var(--muted)]">
          {current.unallocated_minor > 0
            ? `${formatMoney(current.unallocated_minor)} of expected income is not assigned to a category.`
            : `Planned spending is ${formatMoney(-current.unallocated_minor)} above expected income.`}
        </p>
      ) : null}
    </div>
  );
}
