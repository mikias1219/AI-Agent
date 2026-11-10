"use client";

import { Badge } from "@/components/ui/badge";
import { Drawer } from "@/components/ui/drawer";
import type { ActivityEvent } from "@/lib/api/types";
import { formatActivityEvent, formatActivityWhen } from "./format";

export type ActivityDetailDrawerProps = {
  event: ActivityEvent | null;
  open: boolean;
  onClose: () => void;
};

export function ActivityDetailDrawer({ event, open, onClose }: ActivityDetailDrawerProps) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={event ? formatActivityEvent(event.event) : "Activity"}
    >
      {event ? (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">{event.actor}</Badge>
            <time className="text-xs text-[var(--muted)]" dateTime={event.occurred_at}>
              {formatActivityWhen(event.occurred_at)}
            </time>
          </div>
          <dl className="grid grid-cols-[5.5rem_1fr] gap-x-3 gap-y-2 text-sm">
            <dt className="text-[var(--muted)]">Event</dt>
            <dd className="text-[var(--ink)]">{event.event}</dd>
            <dt className="text-[var(--muted)]">Id</dt>
            <dd className="text-[var(--ink)]">{event.id}</dd>
          </dl>
          <div>
            <h3 className="text-sm font-medium text-[var(--ink)]">Details</h3>
            <pre className="mt-2 overflow-auto rounded-[var(--radius)] bg-[var(--canvas)] p-3 text-xs whitespace-pre-wrap text-[var(--ink)]">
              {formatDetails(event.details)}
            </pre>
          </div>
        </div>
      ) : null}
    </Drawer>
  );
}

function formatDetails(details: Record<string, unknown>): string {
  try {
    return JSON.stringify(details, null, 2);
  } catch {
    return "Details could not be displayed.";
  }
}
