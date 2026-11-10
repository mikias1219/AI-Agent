"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { decideApproval, listApprovals } from "@/lib/api/tasks";
import type { Approval, ApprovalDecision } from "@/lib/api/types";

export type NotificationsDrawerProps = {
  open: boolean;
  onClose: () => void;
  approvalsUnavailable: boolean;
  refreshKey?: number;
  onApprovalChanged?: () => void;
};

export function NotificationsDrawer({
  open,
  onClose,
  approvalsUnavailable,
  refreshKey = 0,
  onApprovalChanged,
}: NotificationsDrawerProps) {
  const [items, setItems] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pendingDecision, setPendingDecision] = useState<ApprovalDecision | null>(null);
  const [decideErrors, setDecideErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    listApprovals()
      .then((rows) => {
        if (!cancelled) setItems(rows.filter((r) => r.actionable));
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, refreshKey]);

  useEffect(() => {
    if (!open) {
      setDecideErrors({});
      setPendingDecision(null);
      setBusyId(null);
    }
  }, [open]);

  const decide = useCallback(
    async (id: string, decision: ApprovalDecision) => {
      setBusyId(id);
      setPendingDecision(decision);
      setDecideErrors((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      try {
        await decideApproval(id, decision);
        setItems((prev) => prev.filter((a) => a.id !== id));
        setDecideErrors((prev) => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
        onApprovalChanged?.();
      } catch {
        setDecideErrors((prev) => ({
          ...prev,
          [id]: "Could not record your decision. Try again.",
        }));
      } finally {
        setBusyId(null);
        setPendingDecision(null);
      }
    },
    [onApprovalChanged],
  );

  return (
    <Drawer open={open} onClose={onClose} title="Notifications">
      {open ? (
        <div className="flex flex-col gap-4">
          {approvalsUnavailable ? (
            <p className="text-xs text-[var(--muted)]">Pending approvals could not be loaded.</p>
          ) : null}
          {loading ? (
            <p className="text-sm text-[var(--muted)]">Loading pending approvals…</p>
          ) : items.length === 0 ? (
            <EmptyState title="No notifications" description="New items will show up here." />
          ) : (
            <ul className="flex flex-col gap-3">
              {items.map((approval) => (
                <li key={approval.id}>
                  <ApprovalNotificationItem
                    approval={approval}
                    busy={busyId === approval.id}
                    pending={busyId === approval.id ? pendingDecision : null}
                    error={decideErrors[approval.id] ?? null}
                    onDecide={(decision) => decide(approval.id, decision)}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </Drawer>
  );
}

function ApprovalNotificationItem({
  approval,
  busy,
  pending,
  error,
  onDecide,
}: {
  approval: Approval;
  busy: boolean;
  pending: ApprovalDecision | null;
  error: string | null;
  onDecide: (decision: ApprovalDecision) => void;
}) {
  const argsPreview = summarizeArguments(approval.arguments);
  const when = formatWhen(approval.created_at);

  return (
    <div className="rounded-[var(--radius)] border border-[var(--border)] px-3 py-3">
      <div className="flex flex-col gap-2">
        <div>
          <p className="text-sm font-medium text-[var(--ink)]">{approval.tool_name}</p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {approval.origin}
            {when ? ` · ${when}` : ""}
          </p>
        </div>
        {argsPreview ? (
          <pre className="max-h-32 overflow-auto rounded-[var(--radius)] bg-[var(--canvas)] p-2 text-xs whitespace-pre-wrap text-[var(--ink)]">
            {argsPreview}
          </pre>
        ) : null}
        {error ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button
            variant="danger"
            size="sm"
            disabled={busy}
            loading={pending === "reject"}
            onClick={() => onDecide("reject")}
          >
            Reject
          </Button>
          <Button
            size="sm"
            disabled={busy}
            loading={pending === "approve"}
            onClick={() => onDecide("approve")}
          >
            Approve
          </Button>
        </div>
      </div>
    </div>
  );
}

function summarizeArguments(args: Record<string, unknown>): string {
  try {
    const text = JSON.stringify(args, null, 2);
    if (text.length <= 600) return text;
    return `${text.slice(0, 600)}…`;
  } catch {
    return "";
  }
}

function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
