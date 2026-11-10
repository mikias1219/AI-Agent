"use client";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import type { Approval, ApprovalDecision } from "@/lib/api/types";

export type TaskApproveModalProps = {
  approval: Approval | null;
  open: boolean;
  pending: ApprovalDecision | null;
  error: string | null;
  onClose: () => void;
  onDecide: (decision: ApprovalDecision) => void;
};

export function TaskApproveModal({
  approval,
  open,
  pending,
  error,
  onClose,
  onDecide,
}: TaskApproveModalProps) {
  return (
    <Modal open={open} onClose={pending ? () => undefined : onClose} title="Review approval">
      {approval ? (
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-sm font-medium text-[var(--ink)]">{approval.tool_name}</p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {approval.origin} · {formatWhen(approval.created_at)}
            </p>
          </div>
          <pre className="max-h-56 overflow-auto rounded-[var(--radius)] bg-[var(--canvas)] p-3 text-xs whitespace-pre-wrap text-[var(--ink)]">
            {JSON.stringify(approval.arguments, null, 2)}
          </pre>
          {approval.actionable ? (
            <p className="text-sm text-[var(--muted)]">
              This action is waiting. Approve it to continue, or reject it.
            </p>
          ) : (
            <p className="text-sm text-[var(--muted)]">
              The original turn is no longer waiting. Ask the agent to retry this action.
            </p>
          )}
          {error ? (
            <p className="text-sm text-[var(--danger)]" role="alert">
              {error}
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={onClose} disabled={pending !== null}>
              Close
            </Button>
            {approval.actionable ? (
              <>
                <Button
                  variant="danger"
                  size="sm"
                  disabled={pending !== null}
                  loading={pending === "reject"}
                  onClick={() => onDecide("reject")}
                >
                  Reject
                </Button>
                <Button
                  size="sm"
                  disabled={pending !== null}
                  loading={pending === "approve"}
                  onClick={() => onDecide("approve")}
                >
                  Approve
                </Button>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </Modal>
  );
}

function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
