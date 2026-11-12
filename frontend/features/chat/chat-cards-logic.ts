import type { TrailStep } from "./run-trail";

export type ChatCardKind =
  | "task"
  | "reminder"
  | "plan"
  | "approval"
  | "receipt"
  | "draft"
  | "calendar"
  | "email_sent"
  | "memory_proposal"
  | "search_results"
  | "suggestion";

/** Every card is typed by the tool's `result_type`; tool names are never inspected. */
export type ChatCard = {
  kind: ChatCardKind;
  /** The raw `result_type` the card was derived from (empty when the tool sent none). */
  resultType: string;
  /** Short human text from the tool result's `summary`. */
  summary: string;
  /** Result id when the tool returned one (task id, draft id, approval id, plan id). */
  id?: string;
  /** True when the `result_type` was not recognised and the card fell back to a receipt. */
  fallback?: boolean;
  /** Plan cards: steps the plan lists, when the result carries them. */
  steps?: string[];
};

export const CHAT_CARD_LABELS: Record<ChatCardKind, string> = {
  task: "Task",
  reminder: "Reminder",
  plan: "Plan",
  approval: "Approval",
  receipt: "Receipt",
  draft: "Draft",
  calendar: "Calendar",
  email_sent: "Email sent",
  memory_proposal: "Memory",
  search_results: "Search",
  suggestion: "Suggestion",
};

/** Cards that carry primary actions in the UI. */
export function cardHasActions(card: ChatCard): boolean {
  return card.kind === "plan" || (card.kind === "approval" && Boolean(card.id));
}

/** Map a tool `result_type` to a card kind. Unknown or missing types become a receipt. */
export function kindFromResultType(resultType: string | undefined): {
  kind: ChatCardKind;
  fallback: boolean;
} {
  switch (resultType) {
    case "task":
      return { kind: "task", fallback: false };
    case "reminder":
      return { kind: "reminder", fallback: false };
    case "plan":
      return { kind: "plan", fallback: false };
    case "approval":
    case "approval_request":
      return { kind: "approval", fallback: false };
    case "receipt":
      return { kind: "receipt", fallback: false };
    case "email_draft":
      return { kind: "draft", fallback: false };
    case "email_sent":
      return { kind: "email_sent", fallback: false };
    case "calendar_event":
    case "calendar_proposal":
      return { kind: "calendar", fallback: false };
    case "memory_proposal":
      return { kind: "memory_proposal", fallback: false };
    case "search_results":
      return { kind: "search_results", fallback: false };
    case "suggestion":
      return { kind: "suggestion", fallback: false };
    default:
      // "generic", empty, undefined and anything new: show the honest receipt.
      return { kind: "receipt", fallback: resultType !== "generic" };
  }
}

/** Derive chat cards from structured tool result_type (AG-VER-04). Failed steps get no card. */
export function cardsFromSteps(steps: TrailStep[] | undefined): ChatCard[] {
  if (!steps?.length) return [];
  const cards: ChatCard[] = [];
  for (const step of steps) {
    if (step.status !== "ok") continue;
    const { kind, fallback } = kindFromResultType(step.resultType);
    const summary = (
      step.resultSummary?.trim() ||
      step.detail?.trim() ||
      step.name ||
      "Completed"
    ).slice(0, 160);
    const card: ChatCard = { kind, resultType: step.resultType ?? "", summary };
    if (step.resultId) card.id = step.resultId;
    if (fallback) card.fallback = true;
    if (kind === "plan" && step.resultSteps?.length) card.steps = step.resultSteps;
    cards.push(card);
  }
  return cards;
}

export type ThreadGroup<T> = { label: "Today" | "Earlier"; items: T[] };

/** Split threads (already newest first) into TODAY / EARLIER by their creation day. */
export function groupThreads<T extends { created_at: string }>(
  threads: T[],
  now: Date = new Date(),
): ThreadGroup<T>[] {
  const today: T[] = [];
  const earlier: T[] = [];
  for (const thread of threads) {
    const created = new Date(thread.created_at);
    const sameDay =
      created.getFullYear() === now.getFullYear() &&
      created.getMonth() === now.getMonth() &&
      created.getDate() === now.getDate();
    (sameDay ? today : earlier).push(thread);
  }
  const groups: ThreadGroup<T>[] = [];
  if (today.length) groups.push({ label: "Today", items: today });
  if (earlier.length) groups.push({ label: "Earlier", items: earlier });
  return groups;
}

/** Thread label: the first user message when known, else the start time. */
export function threadTitle(
  firstUserMessage: string | undefined,
  createdAt: string,
  now: Date = new Date(),
): string {
  const text = firstUserMessage?.trim().replace(/\s+/g, " ");
  if (text) return text.length > 48 ? `${text.slice(0, 47)}…` : text;
  const created = new Date(createdAt);
  if (Number.isNaN(created.getTime())) return "Conversation";
  const sameDay = created.toDateString() === now.toDateString();
  return sameDay
    ? `Chat at ${created.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`
    : `Chat on ${created.toLocaleDateString([], { month: "short", day: "numeric" })}`;
}
