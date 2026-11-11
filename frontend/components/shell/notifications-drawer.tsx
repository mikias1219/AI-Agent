"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { listApprovals } from "@/lib/api/approvals";
import type { Approval } from "@/lib/api/types";

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

  const replaceItem = useCallback((replacement: Approval) => {
    setItems((prev) =>
      prev.map((item) => (item.id === replacement.edited_from ? replacement : item)),
    );
  }, []);

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
                  <ApprovalCard
                    approval={approval}
                    onDecided={() => {
                      setItems((prev) => prev.filter((item) => item.id !== approval.id));
                      onApprovalChanged?.();
                    }}
                    onReplaced={replaceItem}
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
