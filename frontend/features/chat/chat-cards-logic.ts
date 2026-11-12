import type { TrailStep } from "./run-trail";

export type ChatCard =
  | { kind: "task"; title: string }
  | { kind: "reminder"; title: string }
  | { kind: "receipt"; summary: string }
  | { kind: "draft"; summary: string }
  | { kind: "calendar"; summary: string }
  | { kind: "email_sent"; summary: string }
  | { kind: "memory_proposal"; summary: string }
  | { kind: "search_results"; summary: string }
  | { kind: "generic"; summary: string };

export const CHAT_CARD_LABELS: Record<ChatCard["kind"], string> = {
  task: "Task",
  reminder: "Reminder",
  receipt: "Receipt",
  draft: "Draft",
  calendar: "Calendar",
  email_sent: "Email sent",
  memory_proposal: "Memory",
  search_results: "Search",
  generic: "Result",
};

function kindFromResultType(resultType: string | undefined): ChatCard["kind"] {
  switch (resultType) {
    case "task":
      return "task";
    case "reminder":
      return "reminder";
    case "email_draft":
      return "draft";
    case "email_sent":
      return "email_sent";
    case "calendar_event":
    case "calendar_proposal":
      return "calendar";
    case "memory_proposal":
      return "memory_proposal";
    case "search_results":
      return "search_results";
    case "generic":
    case undefined:
    case "":
      return "generic";
    default:
      return "generic";
  }
}

/** Derive chat cards from structured tool result_type (AG-VER-04). */
export function cardsFromSteps(steps: TrailStep[] | undefined): ChatCard[] {
  if (!steps?.length) return [];
  const cards: ChatCard[] = [];
  for (const step of steps) {
    if (step.status !== "ok") continue;
    const kind = kindFromResultType(step.resultType);
    const summary = step.resultSummary?.trim() || step.detail?.trim() || step.name || "Completed";
    if (kind === "task" || kind === "reminder") {
      cards.push({ kind, title: summary.slice(0, 120) });
    } else {
      cards.push({ kind, summary: summary.slice(0, 160) });
    }
  }
  return cards;
}
