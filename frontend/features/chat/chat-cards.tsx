"use client";

import { cardsFromSteps, CHAT_CARD_LABELS, type ChatCard } from "./chat-cards-logic";

export type { ChatCard };
export { cardsFromSteps };

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
            {CHAT_CARD_LABELS[card.kind]}
          </p>
          <p className="mt-1 text-[var(--ink)]">{"title" in card ? card.title : card.summary}</p>
        </li>
      ))}
    </ul>
  );
}
