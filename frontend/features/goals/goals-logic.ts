import type { GoalStatus, Plan, PlanStatus, PlanStepStatus } from "@/lib/api/goals";
import type { StatusChipTone } from "@/components/ui/status-chip";

export const GOAL_STATUS_LABEL: Record<GoalStatus, string> = {
  active: "Active",
  paused: "Paused",
  done: "Done",
};

export const PLAN_STATUS_LABEL: Record<PlanStatus, string> = {
  proposed: "Waiting for your OK",
  approved: "Approved",
  done: "Done",
  cancelled: "Cancelled",
};

export const STEP_STATUS_LABEL: Record<PlanStepStatus, string> = {
  planned: "Planned",
  running: "Running",
  needs_ok: "Needs your OK",
  done: "Done",
  failed: "Failed",
};

export function goalTone(status: GoalStatus): StatusChipTone {
  return status === "active" ? "accent" : status === "done" ? "success" : "neutral";
}

export function stepTone(status: PlanStepStatus): StatusChipTone {
  switch (status) {
    case "needs_ok":
      return "warning";
    case "done":
      return "success";
    case "failed":
      return "danger";
    case "running":
      return "accent";
    default:
      return "neutral";
  }
}

export function planTone(status: PlanStatus): StatusChipTone {
  return status === "proposed"
    ? "warning"
    : status === "approved"
      ? "accent"
      : status === "done"
        ? "success"
        : "neutral";
}

/** Whole-number percentage for a 0..1 progress value (clamped). */
export function progressPercent(progress: number): number {
  if (!Number.isFinite(progress)) return 0;
  return Math.round(Math.min(1, Math.max(0, progress)) * 100);
}

/** What a plan approval will and will not authorize, counted from the plan's own steps. */
export function approvalBreakdown(plan: Pick<Plan, "steps">): {
  authorized: number;
  needsOk: number;
} {
  const needsOk = plan.steps.filter(
    (s) => s.access_kind === "execute" || s.access_kind === "destructive",
  ).length;
  return { authorized: plan.steps.length - needsOk, needsOk };
}

/** One honest sentence about the result of approving a plan. */
export function approvalNote(plan: Pick<Plan, "steps">): string {
  const { authorized, needsOk } = approvalBreakdown(plan);
  const base = `${authorized} read/prepare ${authorized === 1 ? "step is" : "steps are"} authorized.`;
  if (needsOk === 0) return base;
  return `${base} ${needsOk} ${needsOk === 1 ? "step" : "steps"} that send, change or delete still need${needsOk === 1 ? "s" : ""} your OK when reached.`;
}
