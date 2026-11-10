import { api } from "./client";
import type {
  Approval,
  ApprovalDecision,
  ApprovalDecisionResponse,
  Task,
  TaskStatus,
} from "./types";

export type CreateTaskInput = {
  title: string;
  description?: string;
};

export async function listTasks(): Promise<Task[]> {
  return api<Task[]>("/tasks");
}

export async function createTask(input: CreateTaskInput): Promise<Task> {
  const body: { title: string; description?: string } = { title: input.title };
  if (input.description !== undefined) body.description = input.description;
  return api<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function patchTask(id: string, body: { status: TaskStatus }): Promise<Task> {
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
