"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonClassName } from "@/components/ui/button";
import { decideApproval } from "@/lib/api/approvals";
import { apiErrorMessage } from "@/lib/api/client";
import { approvePlan, cancelPlan, type Plan } from "@/lib/api/goals";
import type { ApprovalDecision, ApprovalDecisionResponse } from "@/lib/api/types";
import {
  cardsFromSteps,
  CHAT_CARD_LABELS,
  type ChatCard,
  type ChatCardKind,
} from "./chat-cards-logic";
import { approvalNote } from "@/features/goals/goals-logic";

export type { ChatCard };
export { cardsFromSteps };

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
  const planId = card.id;
  const [busy, setBusy] = useState<"approve" | "cancel" | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(action: "approve" | "cancel") {
    if (!planId) return;
    setError(null);
    setBusy(action);
    try {
      setPlan(action === "approve" ? await approvePlan(planId) : await cancelPlan(planId));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  const steps = plan ? plan.steps.map((s) => s.title) : card.steps;
  return (
    <div className="mt-2">
      {steps?.length ? (
        <ol className="mb-2 list-decimal pl-5 text-[var(--muted)]">
          {steps.map((step, index) => (
            <li key={`${index}-${step}`}>{step}</li>
          ))}
        </ol>
      ) : null}
      {plan?.status === "approved" ? (
        <p className="text-xs text-[var(--muted)]" role="status">
          Approved. {approvalNote(plan)}
        </p>
      ) : plan?.status === "cancelled" ? (
        <p className="text-xs text-[var(--muted)]" role="status">
          Plan cancelled.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={!planId || busy !== null}
            onClick={() => void decide("approve")}
          >
            {busy === "approve" ? "Approving…" : "Approve plan"}
          </Button>
          <Link href="/goals" className={buttonClassName("secondary", "sm")}>
            Edit
          </Link>
          <Button
            size="sm"
            variant="secondary"
            disabled={!planId || busy !== null}
            onClick={() => void decide("cancel")}
          >
            {busy === "cancel" ? "Cancelling…" : "Cancel"}
          </Button>
        </div>
      )}
      {error ? (
        <p className="mt-1 text-xs text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}
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
