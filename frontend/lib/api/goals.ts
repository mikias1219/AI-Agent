import { api } from "./client";

export type GoalStatus = "active" | "paused" | "done";
export type PlanStatus = "proposed" | "approved" | "done" | "cancelled";
export type PlanStepStatus = "planned" | "running" | "needs_ok" | "done" | "failed";
export type AccessKind = "read" | "prepare" | "execute" | "destructive";

export type PlanStep = {
  id: string;
  title: string;
  tool_name: string | null;
  access_kind: AccessKind;
  status: PlanStepStatus;
  depends_on: string[];
};

export type Plan = {
  id: string;
  goal_id: string | null;
  title: string;
  status: PlanStatus;
  steps: PlanStep[];
  created_at: string | null;
  updated_at: string | null;
  approved_at: string | null;
};

export type Goal = {
  id: string;
  title: string;
  success_criteria: string[];
  progress: number;
  status: GoalStatus;
  next_step: string;
  created_at: string | null;
  updated_at: string | null;
  /** Only present on the detail endpoint and after create/patch. */
  plans?: Plan[];
};

export type CreateGoalInput = {
  title: string;
  success_criteria?: string[];
  next_step?: string;
};

export type PatchGoalInput = Partial<{
  title: string;
  success_criteria: string[];
  progress: number;
  status: GoalStatus;
  next_step: string;
}>;

export async function listGoals(status?: GoalStatus): Promise<Goal[]> {
  return api<Goal[]>(status ? `/goals?status=${status}` : "/goals");
}

export async function getGoal(id: string): Promise<Goal> {
  return api<Goal>(`/goals/${id}`);
}

export async function createGoal(input: CreateGoalInput): Promise<Goal> {
  return api<Goal>("/goals", { method: "POST", body: JSON.stringify(input) });
}

export async function patchGoal(id: string, input: PatchGoalInput): Promise<Goal> {
  return api<Goal>(`/goals/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export async function listPlans(goalId?: string): Promise<Plan[]> {
  return api<Plan[]>(goalId ? `/plans?goal_id=${goalId}` : "/plans");
}

/** Approving authorizes read/prepare steps only; execute/destructive steps stay `needs_ok`. */
export async function approvePlan(id: string): Promise<Plan> {
  return api<Plan>(`/plans/${id}/approve`, { method: "POST", body: "{}" });
}

export async function cancelPlan(id: string): Promise<Plan> {
  return api<Plan>(`/plans/${id}/cancel`, { method: "POST", body: "{}" });
}
