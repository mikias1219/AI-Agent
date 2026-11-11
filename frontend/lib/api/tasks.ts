import { api } from "./client";
import type {
  Approval,
  ApprovalDecision,
  ApprovalDecisionResponse,
  Task,
  TaskPriority,
  TaskStatus,
} from "./types";

export type TaskViewParam = "today" | "upcoming" | "overdue";

export type ListTasksParams = {
  view?: TaskViewParam;
  status?: TaskStatus;
  priority?: TaskPriority;
  q?: string;
};

export type CreateTaskInput = {
  title: string;
  description?: string;
  priority?: TaskPriority;
  /** Local datetime without zone (e.g. `2026-11-12T09:00`); the server reads it in the owner timezone. */
  due_at?: string;
};

export type PatchTaskInput = {
  status?: TaskStatus;
  title?: string;
  description?: string;
  priority?: TaskPriority;
  /** `null` clears the due date. */
  due_at?: string | null;
};

export function taskListPath(params: ListTasksParams = {}): string {
  const query = new URLSearchParams();
  if (params.view) query.set("view", params.view);
  if (params.status) query.set("status", params.status);
  if (params.priority) query.set("priority", params.priority);
  if (params.q?.trim()) query.set("q", params.q.trim());
  const qs = query.toString();
  return qs ? `/tasks?${qs}` : "/tasks";
}

export async function listTasks(params: ListTasksParams = {}): Promise<Task[]> {
  return api<Task[]>(taskListPath(params));
}

export async function createTask(input: CreateTaskInput): Promise<Task> {
  const body: CreateTaskInput = { title: input.title };
  if (input.description !== undefined) body.description = input.description;
  if (input.priority !== undefined && input.priority !== "none") body.priority = input.priority;
  if (input.due_at) body.due_at = input.due_at;
  return api<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function patchTask(id: string, body: PatchTaskInput): Promise<Task> {
  return api<Task>(`/tasks/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function listApprovals(): Promise<Approval[]> {
  return api<Approval[]>("/approvals");
}

export async function decideApproval(
  id: string,
  decision: ApprovalDecision,
): Promise<ApprovalDecisionResponse> {
  return api<ApprovalDecisionResponse>(`/approvals/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    body: JSON.stringify({ approve: decision === "approve" }),
  });
}
