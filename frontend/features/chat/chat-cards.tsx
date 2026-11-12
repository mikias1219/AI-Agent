"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { decideApproval } from "@/lib/api/approvals";
import { apiErrorMessage } from "@/lib/api/client";
import type { ApprovalDecision, ApprovalDecisionResponse } from "@/lib/api/types";
import {
  cardsFromSteps,
  CHAT_CARD_LABELS,
  type ChatCard,
  type ChatCardKind,
} from "./chat-cards-logic";

export type { ChatCard };
export { cardsFromSteps };

const PLAN_NOTE = "Plan approval arrives with Goals & Plans.";

export type ChatCardsProps = {
  cards: ChatCard[];
  /** Called after an approval card's Approve/Deny was recorded by the server. */
  onApprovalDecided?: (response: ApprovalDecisionResponse) => void;
};

export function ChatCards({ cards, onApprovalDecided }: ChatCardsProps) {
  if (cards.length === 0) return null;
  return (
    <ul className="mt-3 flex flex-col gap-2">
      {cards.map((card, index) => (
        <li
          key={`${card.kind}-${card.id ?? index}-${index}`}
          data-card-kind={card.kind}
          className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm"
        >
          <div className="flex items-center gap-2">
            <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">
              {CHAT_CARD_LABELS[card.kind]}
            </p>
            {card.fallback ? <Badge tone="neutral">{card.resultType || "untyped"}</Badge> : null}
          </div>
          <p className="mt-1 text-[var(--ink)]">{card.summary}</p>
          {card.kind === "plan" ? <PlanActions card={card} /> : null}
          {card.kind === "approval" && card.id ? (
            <ApprovalActions approvalId={card.id} onDecided={onApprovalDecided} />
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function PlanActions({ card }: { card: ChatCard }) {
  return (
    <div className="mt-2">
      {card.steps?.length ? (
        <ol className="mb-2 list-decimal pl-5 text-[var(--muted)]">
          {card.steps.map((step, index) => (
            <li key={`${index}-${step}`}>{step}</li>
          ))}
        </ol>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled title={PLAN_NOTE}>
          Approve plan
        </Button>
        <Button size="sm" variant="secondary" disabled title={PLAN_NOTE}>
          Edit
        </Button>
        <Button size="sm" variant="secondary" disabled title={PLAN_NOTE}>
          Cancel
        </Button>
      </div>
      <p className="mt-1 text-xs text-[var(--muted)]">{PLAN_NOTE}</p>
    </div>
  );
}

function ApprovalActions({
  approvalId,
  onDecided,
}: {
  approvalId: string;
  onDecided?: (response: ApprovalDecisionResponse) => void;
}) {
  const [busy, setBusy] = useState<ApprovalDecision | null>(null);
  const [done, setDone] = useState<ApprovalDecision | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: ApprovalDecision) {
    setError(null);
    setBusy(decision);
    try {
      const response = await decideApproval(approvalId, decision);
      setDone(decision);
      onDecided?.(response);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  if (done) {
    return (
      <p className="mt-2 text-xs text-[var(--muted)]">
        {done === "approve" ? "Approved." : "Denied."}
      </p>
    );
  }

  return (
    <div className="mt-2">
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={busy !== null} onClick={() => void decide("approve")}>
          {busy === "approve" ? "Approving…" : "Approve"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void decide("reject")}
        >
          {busy === "reject" ? "Denying…" : "Deny"}
        </Button>
      </div>
      {error ? (
        <p className="mt-1 text-xs text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export type { ChatCardKind };
