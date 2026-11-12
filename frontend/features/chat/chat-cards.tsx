"use client";

import type { TrailStep } from "./run-trail";

export type ChatCard =
  | { kind: "task"; title: string }
  | { kind: "receipt"; summary: string }
  | { kind: "draft"; summary: string }
  | { kind: "calendar"; summary: string };

/** Derive simple chat cards from finished tool steps (UX-04). */
export function cardsFromSteps(steps: TrailStep[] | undefined): ChatCard[] {
  if (!steps?.length) return [];
  const cards: ChatCard[] = [];
  for (const step of steps) {
    if (step.status !== "ok") continue;
    const name = step.name.toLowerCase();
    const detail = step.detail?.trim() || "";
    if (name.includes("task_create") || name === "create_task") {
      cards.push({ kind: "task", title: detail.slice(0, 120) || "Task created" });
    } else if (name.includes("send") || name.includes("telegram_send")) {
      cards.push({ kind: "receipt", summary: detail.slice(0, 160) || "Action completed" });
    } else if (name.includes("draft") || name.includes("gmail_create_draft")) {
      cards.push({ kind: "draft", summary: detail.slice(0, 160) || "Draft ready" });
    } else if (name.includes("calendar")) {
      cards.push({ kind: "calendar", summary: detail.slice(0, 160) || "Calendar proposal" });
    }
  }
  return cards;
}

export function ChatCards({ cards }: { cards: ChatCard[] }) {
  if (cards.length === 0) return null;
  return (
    <ul className="mt-3 flex flex-col gap-2">
      {cards.map((card, index) => (
        <li
          key={`${card.kind}-${index}`}
          className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm"
        >
          <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">
            {card.kind === "task"
              ? "Task"
              : card.kind === "receipt"
                ? "Receipt"
                : card.kind === "draft"
                  ? "Draft"
                  : "Calendar"}
          </p>
          <p className="mt-1 text-[var(--ink)]">
            {card.kind === "task" ? card.title : card.summary}
          </p>
        </li>
      ))}
    </ul>
  );
}
