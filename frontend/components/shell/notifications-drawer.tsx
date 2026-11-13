"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button, buttonClassName } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { StatusChip } from "@/components/ui/status-chip";
import { formatActivityEvent, formatActivityWhen } from "@/features/activity/format";
import { apiErrorMessage } from "@/lib/api/client";
import { listActivity } from "@/lib/api/activity";
import { getInbox, type InboxItem } from "@/lib/api/inbox";
import type { ActivityEvent } from "@/lib/api/types";

export type NotificationsDrawerProps = {
  open: boolean;
  onClose: () => void;
};

export function NotificationsDrawer({ open, onClose }: NotificationsDrawerProps) {
  const [needsYou, setNeedsYou] = useState<InboxItem[]>([]);
  const [updates, setUpdates] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      getInbox("open").catch(() => null),
      listActivity({ limit: 8 }).catch(() => [] as ActivityEvent[]),
    ])
      .then(([inbox, activity]) => {
        if (cancelled) return;
        setNeedsYou((inbox?.items ?? []).slice(0, 5));
        setUpdates(activity.slice(0, 5));
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(apiErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  return (
    <Drawer open={open} onClose={onClose} title="Notifications">
      <div className="flex flex-col gap-5">
        <p className="text-xs text-[var(--muted)]">A short list. The work happens in Inbox.</p>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <Spinner size="sm" /> Loading…
          </div>
        ) : null}

        {error ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}

        <section aria-labelledby="bell-needs-you">
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3
              id="bell-needs-you"
              className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase"
            >
              Needs you · {needsYou.length}
            </h3>
          </div>
          {needsYou.length === 0 && !loading ? (
            <EmptyState
              title="Nothing waiting"
              description="Approvals and suggestions will show here."
            />
          ) : (
            <ul className="flex flex-col gap-2">
              {needsYou.map((item) => (
                <li
                  key={item.id}
                  className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-[var(--ink)]">{item.title}</p>
                    <StatusChip tone="warning">
                      {item.kind === "approval" ? "Approval" : "Suggestion"}
                    </StatusChip>
                  </div>
                  <Link
                    href="/inbox"
                    onClick={onClose}
                    className="mt-2 inline-block text-xs text-[var(--accent)] underline-offset-2 hover:underline"
                  >
                    Review
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="bell-updates">
          <h3
            id="bell-updates"
            className="mb-2 text-xs font-medium tracking-wide text-[var(--muted)] uppercase"
          >
            Updates
          </h3>
          {updates.length === 0 && !loading ? (
            <p className="text-sm text-[var(--muted)]">No recent updates.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {updates.map((event) => (
                <li key={event.id} className="text-sm text-[var(--ink)]">
                  <p className="font-medium">{formatActivityEvent(event.event)}</p>
                  <time className="text-xs text-[var(--muted)]" dateTime={event.occurred_at}>
                    {formatActivityWhen(event.occurred_at)}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="flex flex-wrap gap-2 border-t border-[var(--border)] pt-3">
          <Link href="/inbox" onClick={onClose} className={buttonClassName("primary", "sm")}>
            Open Inbox
          </Link>
          <Button type="button" size="sm" variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Drawer>
  );
}
