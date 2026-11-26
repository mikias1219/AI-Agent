"use client";

import { FormEvent, useState } from "react";
import { PiggyBank } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { StatusChip } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { contributeToGoal, createSavingsGoal, listSavingsGoals } from "@/lib/api/finance";
import { formatMoney, parseAmount } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";

export function GoalsTab() {
  const { toast } = useToast();
  const goals = useLoad(listSavingsGoals);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [monthly, setMonthly] = useState("");
  const [add, setAdd] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const targetValue = parseAmount(target);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || targetValue === null) return;
    setBusy(true);
    try {
      await createSavingsGoal({
        name: name.trim(),
        target: targetValue,
        monthly_contribution: parseAmount(monthly) ?? undefined,
      });
      setName("");
      setTarget("");
      setMonthly("");
      void goals.reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  async function contribute(id: string) {
    const value = parseAmount(add[id] ?? "");
    if (value === null) return;
    try {
      await contributeToGoal(id, value);
      setAdd({ ...add, [id]: "" });
      void goals.reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  if (goals.error)
    return (
      <ErrorBlock what="savings goals" message={goals.error} onRetry={() => void goals.reload()} />
    );
  if (!goals.data) return <CardSkeleton rows={3} />;

  return (
    <div className="flex flex-col gap-5">
      {goals.data.length === 0 ? (
        <EmptyState
          icon={PiggyBank}
          title="No savings goals yet"
          description="Set a target, like an emergency fund or a laptop, and add to it as you save."
        />
      ) : (
        goals.data.map((g) => (
          <Card
            key={g.id}
            id={`goal-${g.id}`}
            title={g.name}
            description={`${formatMoney(g.saved_minor)} of ${formatMoney(g.target_minor)}`}
            action={
              g.on_track === null ? undefined : (
                <StatusChip tone={g.on_track ? "success" : "warning"}>
                  {g.on_track ? "On track" : "Behind"}
                </StatusChip>
              )
            }
          >
            <div className="flex flex-col gap-3">
              <div
                className="h-2 overflow-hidden rounded-full bg-[var(--subtle)]"
                role="progressbar"
                aria-label={`${g.name} progress`}
                aria-valuenow={Math.round(g.progress_pct)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full rounded-full bg-[var(--accent)]"
                  style={{ width: `${g.progress_pct}%` }}
                />
              </div>
              <p className="text-xs text-[var(--muted)]">
                {g.projected_completion
                  ? `At ${formatMoney(g.monthly_contribution_minor)} a month, done by ${new Date(g.projected_completion).toLocaleDateString(undefined, { month: "long", year: "numeric" })}.`
                  : "Set a monthly amount to see when you will reach it."}
              </p>
              <div className="flex gap-2">
                <label className="sr-only" htmlFor={`add-${g.id}`}>
                  Add to {g.name}
                </label>
                <Input
                  id={`add-${g.id}`}
                  inputMode="decimal"
                  className="min-h-11 max-w-40"
                  placeholder="Amount"
                  value={add[g.id] ?? ""}
                  onChange={(e) => setAdd({ ...add, [g.id]: e.target.value })}
                />
                <Button
                  variant="secondary"
                  className="min-h-11"
                  disabled={parseAmount(add[g.id] ?? "") === null}
                  onClick={() => void contribute(g.id)}
                >
                  Add savings
                </Button>
              </div>
            </div>
          </Card>
        ))
      )}
      <Card id="goal-new" title="New savings goal">
        <form onSubmit={create} className="grid gap-3 sm:grid-cols-3 sm:items-end">
          <Field label="Name" htmlFor="sg-name">
            <Input
              id="sg-name"
              className="min-h-11"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Emergency fund"
            />
          </Field>
          <Field label="Target" htmlFor="sg-target">
            <Input
              id="sg-target"
              inputMode="decimal"
              className="min-h-11"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="50000"
            />
          </Field>
          <Field label="Monthly (optional)" htmlFor="sg-monthly">
            <Input
              id="sg-monthly"
              inputMode="decimal"
              className="min-h-11"
              value={monthly}
              onChange={(e) => setMonthly(e.target.value)}
              placeholder="3000"
            />
          </Field>
          <div className="sm:col-span-3">
            <Button
              type="submit"
              className="min-h-11"
              loading={busy}
              disabled={!name.trim() || targetValue === null}
            >
              Create goal
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
