import { api } from "./client";
import type { Recurrence } from "./habits";
import type { Task, TaskPriority, TaskStatus } from "./types";

export type TaskOutcome = "achieved" | "partial" | "missed" | "skipped";

/** Task plus the achievement, day and calendar fields (docs/LIFE_API_CONTRACT.md section 7). */
export type LifeTask = Task & {
  plan_date?: string;
  target_value?: number | null;
  target_unit?: string;
  actual_value?: number | null;
  outcome?: TaskOutcome | null;
  outcome_note?: string;
  calendar_event_id?: string | null;
  calendar_synced_at?: string | null;
  recurrence?: Recurrence | null;
};

export type TaskViewParam = "today" | "upcoming" | "overdue";

export type ListTasksParams = {
  view?: TaskViewParam;
  status?: TaskStatus;
  priority?: TaskPriority;
  q?: string;
  plan_date?: string;
  from?: string;
  to?: string;
};

export type CreateTaskInput = {
  title: string;
  description?: string;
  priority?: TaskPriority;
  /** Local datetime without zone (e.g. `2026-11-12T09:00`); the server reads it in the owner timezone. */
  due_at?: string;
  plan_date?: string;
  target_value?: number;
  target_unit?: string;
  /** Finishing the task creates the next one on this schedule. */
  recurrence?: Recurrence;
  parent_id?: string;
  blocked_by?: string[];
};

export type PatchTaskInput = {
  status?: TaskStatus;
  title?: string;
  description?: string;
  priority?: TaskPriority;
  parent_id?: string | null;
  blocked_by?: string[];
  /** `null` clears the due date. */
  due_at?: string | null;
  plan_date?: string;
  target_value?: number | null;
  target_unit?: string;
  actual_value?: number | null;
  outcome?: TaskOutcome | null;
  outcome_note?: string;
};

export type CompleteTaskInput = {
  outcome?: TaskOutcome;
  actual_value?: number;
  note?: string;
};

export function taskListPath(params: ListTasksParams = {}): string {
  const query = new URLSearchParams();
  if (params.view) query.set("view", params.view);
  if (params.status) query.set("status", params.status);
  if (params.priority) query.set("priority", params.priority);
  if (params.plan_date) query.set("plan_date", params.plan_date);
  if (params.from) query.set("from", params.from);
  if (params.to) query.set("to", params.to);
  if (params.q?.trim()) query.set("q", params.q.trim());
  const qs = query.toString();
  return qs ? `/tasks?${qs}` : "/tasks";
}

export async function listTasks(params: ListTasksParams = {}): Promise<LifeTask[]> {
  return api<LifeTask[]>(taskListPath(params));
}

export async function createTask(input: CreateTaskInput): Promise<LifeTask> {
  const body: CreateTaskInput = { title: input.title };
  if (input.description !== undefined) body.description = input.description;
  if (input.priority !== undefined && input.priority !== "none") body.priority = input.priority;
  if (input.due_at) body.due_at = input.due_at;
  if (input.plan_date) body.plan_date = input.plan_date;
  if (input.recurrence) body.recurrence = input.recurrence;
  if (input.parent_id) body.parent_id = input.parent_id;
  if (input.blocked_by?.length) body.blocked_by = input.blocked_by;
  if (input.target_value !== undefined && input.target_value > 0) {
    body.target_value = input.target_value;
    if (input.target_unit?.trim()) body.target_unit = input.target_unit.trim();
  }
  return api<LifeTask>("/tasks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function patchTask(id: string, body: PatchTaskInput): Promise<LifeTask> {
  return api<LifeTask>(`/tasks/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function completeTask(id: string, input: CompleteTaskInput = {}): Promise<LifeTask> {
  return api<LifeTask>(`/tasks/${encodeURIComponent(id)}/complete`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}
