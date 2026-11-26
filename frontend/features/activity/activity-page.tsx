"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button, buttonClassName } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { StatusChip, type StatusChipTone } from "@/components/ui/status-chip";
import { activityExportUrl, listActivity } from "@/lib/api/activity";
import { apiErrorMessage } from "@/lib/api/client";
import type { ActivityEvent } from "@/lib/api/types";
import { ActivityDetailDrawer } from "./activity-detail-drawer";
import { formatActivityEvent, formatActivityWhen } from "./format";

const ACTIVITY_PAGE_SIZE = 15;
const FETCH_LIMIT = 200;

type ActivityChipId = "all" | "chat" | "routines" | "telegram" | "review";

const ACTIVITY_CHIPS: {
  id: ActivityChipId;
  label: string;
  origin?: string;
  status?: string;
  eventPrefixes?: string[];
}[] = [
  { id: "all", label: "All" },
  { id: "chat", label: "Chat", origin: "dashboard" },
  {
    id: "routines",
    label: "Routines",
    eventPrefixes: ["automation.", "scheduler.", "reminder."],
  },
  { id: "telegram", label: "Telegram", origin: "telegram" },
  { id: "review", label: "Needs review", status: "failed" },
];

async function loadActivity(chip: (typeof ACTIVITY_CHIPS)[number]): Promise<ActivityEvent[]> {
  const all: ActivityEvent[] = [];
  const seen = new Set<number>();
  let offset = 0;

  for (let page = 0; page < 25; page += 1) {
    const rows = await listActivity({
      limit: FETCH_LIMIT,
      offset,
      origin: chip.origin,
      status: chip.status,
    });
    let added = 0;
    for (const row of rows) {
      if (seen.has(row.id)) continue;
      if (
        chip.eventPrefixes &&
        !chip.eventPrefixes.some((prefix) => row.event.startsWith(prefix))
      ) {
        continue;
      }
      seen.add(row.id);
      all.push(row);
      added += 1;
    }
    // When filtering by event prefix client-side, an empty page of matches
    // does not mean we ran out of audit rows.
    if (rows.length < FETCH_LIMIT) break;
    if (!chip.eventPrefixes && added === 0) break;
    offset += rows.length;
  }

  all.sort((a, b) => b.id - a.id);
  return all;
}

function statusFor(event: string): { label: string; tone: StatusChipTone } {
  if (event === "run.failed") return { label: "Failed", tone: "danger" };
  if (event === "run.cancelled") return { label: "Stopped", tone: "warning" };
  if (event === "run.completed") return { label: "Done", tone: "success" };
  if (event.includes("blocked")) return { label: "Blocked", tone: "warning" };
  if (event.startsWith("approval.")) return { label: "Decided", tone: "accent" };
  return { label: "Recorded", tone: "neutral" };
}

const COLUMNS: Column<ActivityEvent>[] = [
  {
    id: "event",
    header: "What happened",
    sortValue: (e) => formatActivityEvent(e.event),
    cell: (e) => (
      <span className="font-medium text-[var(--ink)]">{formatActivityEvent(e.event)}</span>
    ),
  },
  {
    id: "status",
    header: "Status",
    width: "w-28",
    sortValue: (e) => statusFor(e.event).label,
    cell: (e) => {
      const st = statusFor(e.event);
      return <StatusChip tone={st.tone}>{st.label}</StatusChip>;
    },
  },
  {
    id: "actor",
    header: "Source",
    width: "w-32",
    hideOnMobile: true,
    sortValue: (e) => e.actor,
    cell: (e) => <span className="text-[var(--muted)]">{e.actor}</span>,
  },
  {
    id: "when",
    header: "When",
    width: "w-44",
    align: "right",
    sortValue: (e) => e.occurred_at,
    cell: (e) => (
      <time className="text-[var(--muted)] tabular-nums" dateTime={e.occurred_at}>
        {formatActivityWhen(e.occurred_at)}
      </time>
    ),
  },
];

export type ActivityPageProps = {
  embedded?: boolean;
};

export function ActivityPage({ embedded = false }: ActivityPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idParam = searchParams.get("id");
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [dismissedId, setDismissedId] = useState<string | null>(null);
  const [chipId, setChipId] = useState<ActivityChipId>("all");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const chip = ACTIVITY_CHIPS.find((item) => item.id === chipId) ?? ACTIVITY_CHIPS[0]!;
    loadActivity(chip)
      .then((rows) => {
        if (!cancelled) setEvents(rows);
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
  }, [reloadKey, chipId]);

  const activeId = idParam && idParam !== dismissedId ? idParam : null;
  const selected = events.find((event) => String(event.id) === activeId) ?? null;
  const missingHighlight = Boolean(activeId) && !loading && !error && !selected;

  function openEvent(event: ActivityEvent) {
    setDismissedId(null);
    router.replace(`/activity?id=${encodeURIComponent(String(event.id))}`, { scroll: false });
  }

  function closeDrawer() {
    if (idParam) setDismissedId(idParam);
    router.replace("/activity", { scroll: false });
  }

  return (
    <div
      className={
        embedded
          ? "flex flex-col gap-4"
          : "mx-auto flex w-full max-w-[var(--content-width)] flex-col gap-4"
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Activity filters">
          {ACTIVITY_CHIPS.map((chip) => {
            const active = chipId === chip.id;
            return (
              <button
                key={chip.id}
                type="button"
                aria-pressed={active}
                onClick={() => setChipId(chip.id)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                  active
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--ink)]"
                }`}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
        <div className="flex gap-2">
          <a
            href={activityExportUrl()}
            download="compass-activity.csv"
            className={buttonClassName("secondary", "sm")}
          >
            Export CSV
          </a>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setReloadKey((key) => key + 1)}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>
      </div>

      {!loading && !error && missingHighlight ? (
        <p className="text-sm text-[var(--muted)]" role="status">
          That activity entry is not in the loaded timeline.
        </p>
      ) : null}

      <Card
        id="activity-table"
        title="Timeline"
        description="Open a row for ids and technical detail."
        flush
      >
        <DataTable
          label="Activity"
          columns={COLUMNS}
          rows={events}
          rowKey={(e) => String(e.id)}
          loading={loading}
          error={error}
          onRetry={() => setReloadKey((key) => key + 1)}
          pageSize={ACTIVITY_PAGE_SIZE}
          onRowClick={openEvent}
          selectedKey={activeId}
          initialSort={{ id: "when", dir: "desc" }}
          empty={{
            title: "No activity yet",
            description: "Actions from chat and tasks will land here.",
          }}
        />
      </Card>

      <ActivityDetailDrawer event={selected} open={selected !== null} onClose={closeDrawer} />
    </div>
  );
}
