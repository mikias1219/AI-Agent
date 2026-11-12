"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { CompactRow } from "@/components/ui/compact-row";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { StatusChip } from "@/components/ui/status-chip";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/lib/api/client";
import {
  approvePlan,
  cancelPlan,
  createGoal,
  getGoal,
  listGoals,
  patchGoal,
  type Goal,
  type GoalStatus,
  type Plan,
} from "@/lib/api/goals";
import {
  approvalNote,
  GOAL_STATUS_LABEL,
  goalTone,
  PLAN_STATUS_LABEL,
  planTone,
  progressPercent,
  STEP_STATUS_LABEL,
  stepTone,
} from "./goals-logic";

export function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [criteria, setCriteria] = useState("");
  const [nextStep, setNextStep] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setGoals(await listGoals());
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) {
      setFormError("Give the goal a title.");
      return;
    }
    setCreating(true);
    setFormError(null);
    try {
      const goal = await createGoal({
        title: title.trim(),
        success_criteria: criteria
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean),
        next_step: nextStep.trim(),
      });
      setGoals((prev) => [goal, ...prev]);
      setTitle("");
      setCriteria("");
      setNextStep("");
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  function onGoalChanged(goal: Goal) {
    setGoals((prev) => prev.map((g) => (g.id === goal.id ? { ...g, ...goal } : g)));
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Goals</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Longer outcomes
        </h1>
        <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
          Goals AURA can plan and track with you. Approving a plan covers reading and preparing
          only; sending, changing or deleting always asks again.
        </p>
      </header>

      <form
        onSubmit={onCreate}
        className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
      >
        <Field label="New goal" htmlFor="goal-title">
          <Input
            id="goal-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Run a 10k by March"
          />
        </Field>
        <Field label="Success criteria (one per line, optional)" htmlFor="goal-criteria">
          <Textarea
            id="goal-criteria"
            value={criteria}
            onChange={(e) => setCriteria(e.target.value)}
            rows={2}
          />
        </Field>
        <Field label="Next step (optional)" htmlFor="goal-next">
          <Input id="goal-next" value={nextStep} onChange={(e) => setNextStep(e.target.value)} />
        </Field>
        <div>
          <Button type="submit" loading={creating}>
            Add goal
          </Button>
        </div>
        {formError ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {formError}
          </p>
        ) : null}
      </form>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Spinner size="sm" /> Loading goals…
        </div>
      ) : null}

      {error ? (
        <div className="flex items-center gap-3" role="alert">
          <p className="text-sm text-[var(--danger)]">{error}</p>
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      ) : null}

      {!loading && !error && goals.length === 0 ? (
        <EmptyState
          title="No goals yet"
          description="Add one above, or ask AURA in Chat to set a goal and propose a plan."
        />
      ) : null}

      {goals.length > 0 ? (
        <ul className="flex flex-col gap-2" aria-label="Goals">
          {goals.map((goal) => (
            <li key={goal.id}>
              <CompactRow
                title={goal.title}
                meta={[`${progressPercent(goal.progress)}%`, goal.next_step || null]
                  .filter(Boolean)
                  .join(" · ")}
                chip={
                  <StatusChip tone={goalTone(goal.status)}>
                    {GOAL_STATUS_LABEL[goal.status]}
                  </StatusChip>
                }
                onClick={() => setSelectedId(goal.id)}
              />
            </li>
          ))}
        </ul>
      ) : null}

      <Drawer open={selectedId !== null} onClose={() => setSelectedId(null)} title="Goal details">
        {selectedId ? (
          <GoalDetail key={selectedId} goalId={selectedId} onChanged={onGoalChanged} />
        ) : null}
      </Drawer>
    </div>
  );
}

function GoalDetail({ goalId, onChanged }: { goalId: string; onChanged: (goal: Goal) => void }) {
  const [goal, setGoal] = useState<Goal | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getGoal(goalId)
      .then((next) => {
        if (!cancelled) setGoal(next);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(apiErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [goalId]);

  async function update(input: Parameters<typeof patchGoal>[1]) {
    setBusy(true);
    setError(null);
    try {
      const next = await patchGoal(goalId, input);
      setGoal(next);
      onChanged(next);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function decide(plan: Plan, action: "approve" | "cancel") {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const next = action === "approve" ? await approvePlan(plan.id) : await cancelPlan(plan.id);
      setGoal((prev) =>
        prev ? { ...prev, plans: prev.plans?.map((p) => (p.id === next.id ? next : p)) } : prev,
      );
      if (action === "approve") setNote(approvalNote(next));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <p className="text-sm text-[var(--danger)]" role="alert">
        {loadError}
      </p>
    );
  }
  if (!goal) {
    return (
      <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
        <Spinner size="sm" /> Loading goal…
      </div>
    );
  }

  const percent = progressPercent(goal.progress);
  const nextStatuses = (["active", "paused", "done"] as GoalStatus[]).filter(
    (s) => s !== goal.status,
  );

  return (
    <div className="flex flex-col gap-5">
      <div>
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-lg font-semibold text-[var(--ink)]">{goal.title}</h3>
          <StatusChip tone={goalTone(goal.status)}>{GOAL_STATUS_LABEL[goal.status]}</StatusChip>
        </div>
        <div
          className="mt-3 h-2 overflow-hidden rounded-full bg-[var(--canvas)]"
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Goal progress"
        >
          <div className="h-full bg-[var(--accent)]" style={{ width: `${percent}%` }} />
        </div>
        <p className="mt-1 text-xs text-[var(--muted)]">{percent}% complete</p>
      </div>

      {goal.next_step ? (
        <section>
          <h4 className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">
            Next step
          </h4>
          <p className="mt-1 text-sm text-[var(--ink)]">{goal.next_step}</p>
        </section>
      ) : null}

      <section>
        <h4 className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">
          Success criteria
        </h4>
        {goal.success_criteria.length ? (
          <ul className="mt-1 list-disc pl-5 text-sm text-[var(--ink)]">
            {goal.success_criteria.map((c, i) => (
              <li key={`${i}-${c}`}>{c}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-[var(--muted)]">None set.</p>
        )}
      </section>

      <div className="flex flex-wrap gap-2">
        {nextStatuses.map((status) => (
          <Button
            key={status}
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => void update({ status, ...(status === "done" ? { progress: 1 } : {}) })}
          >
            {status === "active" ? "Resume" : status === "paused" ? "Pause" : "Mark done"}
          </Button>
        ))}
      </div>

      <section>
        <h4 className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Plans</h4>
        {goal.plans?.length ? (
          <ul className="mt-2 flex flex-col gap-3">
            {goal.plans.map((plan) => (
              <li
                key={plan.id}
                data-plan-id={plan.id}
                className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-[var(--ink)]">{plan.title}</p>
                  <StatusChip tone={planTone(plan.status)}>
                    {PLAN_STATUS_LABEL[plan.status]}
                  </StatusChip>
                </div>
                <ol className="mt-2 flex flex-col gap-1.5">
                  {plan.steps.map((step) => (
                    <li key={step.id} className="flex items-start justify-between gap-2 text-sm">
                      <span className="text-[var(--ink)]">
                        {step.title}
                        <span className="ml-2 text-xs text-[var(--muted)]">{step.access_kind}</span>
                      </span>
                      <StatusChip tone={stepTone(step.status)}>
                        {STEP_STATUS_LABEL[step.status]}
                      </StatusChip>
                    </li>
                  ))}
                </ol>
                {plan.status === "proposed" ? (
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" disabled={busy} onClick={() => void decide(plan, "approve")}>
                      Approve plan
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={busy}
                      onClick={() => void decide(plan, "cancel")}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-[var(--muted)]">
            No plan yet. Ask AURA in Chat to propose one for this goal.
          </p>
        )}
      </section>

      {note ? (
        <p className="text-sm text-[var(--muted)]" role="status">
          {note}
        </p>
      ) : null}
      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
