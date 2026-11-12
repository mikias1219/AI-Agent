import { api } from "./client";
import type { Approval } from "./types";

export type InboxTab = "open" | "done";
export type SuggestionStatus = "new" | "accepted" | "dismissed" | "expired";
export type SuggestionOutcome = "" | "acknowledged" | "done" | "pending_approval";

export type Suggestion = {
  id: string;
  /** What sort of idea this is (e.g. followup); not the inbox item kind. */
  kind: string;
  title: string;
  reason: string;
  /** Required citation: where the idea came from. */
  source: string;
  status: SuggestionStatus;
  proposed_action: { tool_name?: string; arguments?: Record<string, unknown> };
  expires_at: string | null;
  created_at: string | null;
  decided_at: string | null;
  feedback: string;
  outcome: SuggestionOutcome;
  approval_id: string | null;
  actionable: boolean;
};

type InboxItemBase = {
  id: string;
  title: string;
  summary: string;
  status: string;
  actionable: boolean;
  /** Higher means look sooner; the list arrives already ordered. */
  urgency: number;
  created_at: string | null;
  expires_at: string | null;
  decided_at: string | null;
};

export type InboxApprovalItem = InboxItemBase & {
  kind: "approval";
  tool_name: string;
  risk: string;
  untrusted_content: boolean;
  run_id: string | null;
  approval: Approval;
};

export type InboxSuggestionItem = InboxItemBase & {
  kind: "suggestion";
  reason: string;
  source: string;
  suggestion: Suggestion;
};

export type InboxItem = InboxApprovalItem | InboxSuggestionItem;

export type InboxPayload = {
  tab: InboxTab;
  items: InboxItem[];
  counts: { open: number };
};

export type AcceptSuggestionResponse = {
  id: string;
  outcome: SuggestionOutcome;
  summary: string;
  approval_id: string | null;
  suggestion: Suggestion;
};

export async function getInbox(tab: InboxTab = "open"): Promise<InboxPayload> {
  return api<InboxPayload>(`/inbox?tab=${tab}`);
}

export async function acceptSuggestion(id: string): Promise<AcceptSuggestionResponse> {
  return api<AcceptSuggestionResponse>(`/suggestions/${encodeURIComponent(id)}/accept`, {
    method: "POST",
  });
}

export async function dismissSuggestion(
  id: string,
  feedback = "",
): Promise<{ id: string; suggestion: Suggestion }> {
  return api(`/suggestions/${encodeURIComponent(id)}/dismiss`, {
    method: "POST",
    body: JSON.stringify({ feedback }),
  });
}
