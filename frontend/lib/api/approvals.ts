import { api } from "./client";
import type { Approval, ApprovalDecision, ApprovalDecisionResponse } from "./types";

/** Approvals waiting for a decision (the default view). */
export async function listApprovals(): Promise<Approval[]> {
  return api<Approval[]>("/approvals");
}

/** Approve (runs the action once and resumes the run) or reject. Safe to repeat. */
export async function decideApproval(
  id: string,
  decision: ApprovalDecision,
): Promise<ApprovalDecisionResponse> {
  return api<ApprovalDecisionResponse>(`/approvals/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    body: JSON.stringify({ approve: decision === "approve" }),
  });
}

/**
 * Edit before approving. The server replaces this approval with a new one (new hash) that
 * must be approved on its own; the old one can no longer run.
 */
export async function editApproval(id: string, args: Record<string, unknown>): Promise<Approval> {
  return api<Approval>(`/approvals/${encodeURIComponent(id)}/edit`, {
    method: "POST",
    body: JSON.stringify({ arguments: args }),
  });
}
