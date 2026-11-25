"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Banner } from "@/components/ui/banner";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SkeletonRows } from "@/components/ui/skeleton";
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

export type GoalsPageProps = {
  embedded?: boolean;
};

export function GoalsPage(_props: GoalsPageProps = {}) {
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
    <div className="flex flex-col gap-4">
      <form
        onSubmit={onCreate}
        className="flex flex-col gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3"
      >
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            id="goal-title"
            aria-label="New goal"
            className="min-h-11 flex-1"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="New goal, e.g. Run a 10k by March"
          />
          <Input
            id="goal-next"
            aria-label="Next step (optional)"
            className="min-h-11 flex-1"
            value={nextStep}
            onChange={(e) => setNextStep(e.target.value)}
            placeholder="First step (optional)"
          />
          <Button type="submit" className="min-h-11" loading={creating}>
            Add goal
          </Button>
        </div>
        <details className="text-sm">
          <summary className="min-h-8 cursor-pointer text-[var(--muted)] hover:text-[var(--ink)]">
            Add success criteria
          </summary>
          <div className="mt-2">
            <Field label="Success criteria (one per line)" htmlFor="goal-criteria">
              <Textarea
                id="goal-criteria"
                value={criteria}
                onChange={(e) => setCriteria(e.target.value)}
                rows={2}
              />
            </Field>
          </div>
        </details>
        {formError ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {formError}
          </p>
        ) : null}
      </form>

      {loading ? <SkeletonRows count={3} /> : null}

      {error ? (
        <Banner tone="danger" role="alert">
          <div className="flex flex-wrap items-center gap-3">
            <span>Could not load goals: {error}</span>
            <Button size="sm" variant="secondary" onClick={() => void load()}>
              Try again
            </Button>
          </div>
        </Banner>
      ) : null}

      {!loading && !error && goals.length === 0 ? (
        <EmptyState
          title="No goals yet"
          description="Goals are longer outcomes AURA can plan with you. Approving a plan covers reading and preparing only; sending, changing or deleting always asks again."
          action={
            <Button
              variant="secondary"
              onClick={() => document.getElementById("goal-title")?.focus()}
            >
              Write your first goal
            </Button>
          }
        />
      ) : null}

      {!loading && goals.length > 0 ? (
        <ul className="flex flex-col gap-2" aria-label="Goals">
          {goals.map((goal) => {
            const percent = progressPercent(goal.progress);
            return (
              <li key={goal.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(goal.id)}
                  className="flex min-h-14 w-full cursor-pointer flex-col gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-3 text-left transition hover:bg-[var(--canvas)] focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
                >
                  <span className="flex items-center justify-between gap-3">
                    <span className="min-w-0 truncate text-sm font-medium text-[var(--ink)]">
                      {goal.title}
                    </span>
                    <StatusChip tone={goalTone(goal.status)}>
                      {GOAL_STATUS_LABEL[goal.status]}
                    </StatusChip>
                  </span>
                  <span className="flex items-center gap-3">
                    <span
                      className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--canvas)]"
                      aria-hidden
                    >
                      <span
                        className="block h-full bg-[var(--accent)]"
                        style={{ width: `${percent}%` }}
                      />
                    </span>
                    <span className="text-xs text-[var(--muted)]">{percent}%</span>
                  </span>
                  {goal.next_step ? (
                    <span className="truncate text-xs text-[var(--muted)]">
                      Next: {goal.next_step}
                    </span>
                  ) : null}
                </button>
              </li>
            );
          })}
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
                      <span className="min-w-0 text-[var(--ink)]">
                        {step.title}
                        <span className="ml-2 text-xs text-[var(--muted)]">{step.access_kind}</span>
                        {step.result ? (
                          <span className="mt-0.5 block truncate text-xs text-[var(--muted)]">
                            {step.result}
                          </span>
                        ) : null}
                        {step.status === "needs_ok" && step.approval_id ? (
                          <Link
                            href="/inbox"
                            className="mt-0.5 block text-xs font-medium text-[var(--accent)] hover:underline"
                          >
                            Review this step in Needs you
                          </Link>
                        ) : null}
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
