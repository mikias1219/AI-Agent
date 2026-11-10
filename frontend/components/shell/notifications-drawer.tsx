"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { paginate } from "@/lib/pagination";
import {
  NOTIFICATION_PAGE_SIZE,
  notificationsWithApprovals,
  type NotificationKind,
  type ShellNotification,
} from "@/lib/mocks/notifications";

const kindLabel: Record<NotificationKind, string> = {
  approval: "Approval",
  activity: "Activity",
  connection: "Connection",
};

const kindTone: Record<NotificationKind, BadgeTone> = {
  approval: "warning",
  activity: "accent",
  connection: "success",
};

export type NotificationsDrawerProps = {
  open: boolean;
  onClose: () => void;
  approvalCount: number | null;
  approvalsUnavailable: boolean;
};

export function NotificationsDrawer({
  open,
  onClose,
  approvalCount,
  approvalsUnavailable,
}: NotificationsDrawerProps) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!open) setPage(1);
  }, [open]);

  const items = useMemo(() => notificationsWithApprovals(approvalCount), [approvalCount]);
  const pageCount = Math.max(1, Math.ceil(items.length / NOTIFICATION_PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const paged = paginate(items, currentPage, NOTIFICATION_PAGE_SIZE);

  return (
    <Drawer open={open} onClose={onClose} title="Notifications">
      {open ? (
        <div className="flex flex-col gap-4">
          {approvalsUnavailable ? (
            <p className="text-xs text-[var(--muted)]">Pending approvals could not be loaded.</p>
          ) : null}
          {paged.items.length === 0 ? (
            <EmptyState title="No notifications" description="New items will show up here." />
          ) : (
            <ul className="flex flex-col gap-2">
              {paged.items.map((item) => (
                <li key={item.id}>
                  <NotificationItem item={item} onNavigate={onClose} />
                </li>
              ))}
            </ul>
          )}
          <Pagination
            page={paged.page}
            pageSize={paged.pageSize}
            total={paged.total}
            onPageChange={setPage}
          />
        </div>
      ) : null}
    </Drawer>
  );
}

function NotificationItem({
  item,
  onNavigate,
}: {
  item: ShellNotification;
  onNavigate: () => void;
}) {
  const when = formatWhen(item.createdAt);
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className="block rounded-[var(--radius)] border border-[var(--border)] px-3 py-3 transition hover:bg-[var(--canvas)]"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-[var(--ink)]">{item.title}</p>
        <span className="flex shrink-0 gap-1">
          {item.preview ? <Badge tone="neutral">Preview</Badge> : null}
          <Badge tone={kindTone[item.kind]}>{kindLabel[item.kind]}</Badge>
        </span>
      </div>
      <p className="mt-1 text-sm text-[var(--muted)]">{item.body}</p>
      {when ? <p className="mt-2 text-xs text-[var(--muted)]">{when}</p> : null}
    </Link>
  );
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
