"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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

  const wasOpenRef = useRef(false);

  useEffect(() => {
    if (!open) {
      wasOpenRef.current = false;
      return;
    }
    const opening = !wasOpenRef.current;
    wasOpenRef.current = true;
    let cancelled = false;
    if (opening) setLoading(true);
    listApprovals()
      .then((rows) => {
        if (!cancelled) setItems(rows.filter((r) => r.actionable));
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled && opening) setLoading(false);
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
  const title = approvalTitle(approval.tool_name);
  const fields = approvalFields(approval.tool_name, approval.arguments);
  const when = formatWhen(approval.created_at);

  return (
    <div className="rounded-[var(--radius)] border border-[var(--border)] px-3 py-3">
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-sm font-medium text-[var(--ink)]">{title}</p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Needs your approval
            {when ? ` · ${when}` : ""}
          </p>
        </div>
        {fields.length > 0 ? (
          <dl className="space-y-1.5 text-sm">
            {fields.map((field) => (
              <div key={field.label} className="grid grid-cols-[5.5rem_1fr] gap-2">
                <dt className="text-[var(--muted)]">{field.label}</dt>
                <dd className="break-words text-[var(--ink)]">{field.value}</dd>
              </div>
            ))}
          </dl>
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

function approvalTitle(toolName: string): string {
  const titles: Record<string, string> = {
    google_gmail_send: "Send email",
    google_calendar_create: "Create calendar event",
    google_calendar_update: "Update calendar event",
    telegram_send_message: "Send Telegram message",
    task_create: "Create task",
    task_update_status: "Update task",
  };
  return titles[toolName] ?? toolName.replaceAll("_", " ");
}

function approvalFields(
  toolName: string,
  args: Record<string, unknown>,
): { label: string; value: string }[] {
  const str = (key: string, max = 160) => {
    const raw = args[key];
    if (raw === undefined || raw === null) return "";
    const text = String(raw).trim();
    if (!text) return "";
    return text.length > max ? `${text.slice(0, max)}…` : text;
  };
  if (toolName === "google_gmail_send") {
    return [
      { label: "To", value: str("to") },
      { label: "Subject", value: str("subject") },
      { label: "Body", value: str("body", 120) },
    ].filter((f) => f.value);
  }
  if (toolName === "google_calendar_create" || toolName === "google_calendar_update") {
    return [
      { label: "Title", value: str("title") },
      { label: "Starts", value: str("starts_at") },
      { label: "Ends", value: str("ends_at") },
      { label: "Where", value: str("location") },
    ].filter((f) => f.value);
  }
  if (toolName === "telegram_send_message") {
    return [
      { label: "Chat", value: str("chat_id") },
      { label: "Message", value: str("text", 140) },
    ].filter((f) => f.value);
  }
  return Object.entries(args)
    .slice(0, 3)
    .map(([label, value]) => ({
      label: label.replaceAll("_", " "),
      value: String(value).slice(0, 120),
    }));
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
