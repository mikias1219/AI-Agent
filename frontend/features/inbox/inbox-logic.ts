import type { InboxItem, SuggestionOutcome, SuggestionStatus } from "@/lib/api/inbox";

/** What accepting a suggestion actually did, in plain words (never claims more than it did). */
export function outcomeMessage(outcome: SuggestionOutcome, summary = ""): string {
  switch (outcome) {
    case "pending_approval":
      return "Accepted. Nothing has happened yet: the action is waiting for your approval below.";
    case "done":
      return summary ? `Done. ${summary}` : "Done.";
    case "acknowledged":
      return "Noted. Nothing needed to run.";
    default:
      return "Accepted.";
  }
}

export function statusLabel(status: SuggestionStatus | string): string {
  switch (status) {
    case "new":
      return "New";
    case "accepted":
      return "Accepted";
    case "dismissed":
      return "Dismissed";
    case "expired":
      return "Expired";
    default:
      return status;
  }
}

/** Short countdown like "in 3h" or "in 2d"; null when there is no expiry or it already passed. */
export function expiresIn(expiresAt: string | null, now: number): string | null {
  if (!expiresAt) return null;
  const left = new Date(expiresAt).getTime() - now;
  if (Number.isNaN(left) || left <= 0) return null;
  const minutes = Math.ceil(left / 60_000);
  if (minutes < 60) return `in ${minutes}m`;
  const hours = Math.ceil(minutes / 60);
  if (hours < 48) return `in ${hours}h`;
  return `in ${Math.ceil(hours / 24)}d`;
}

/** Item key that stays unique across kinds (an approval and a suggestion may share an id shape). */
export function itemKey(item: Pick<InboxItem, "kind" | "id">): string {
  return `${item.kind}-${item.id}`;
}

/** The open count the sidebar badge shows; falls back to the approvals count if inbox is down. */
export function badgeCount(
  inboxOpen: number | null,
  approvalsPending: number | null,
): number | null {
  return inboxOpen ?? approvalsPending;
}
