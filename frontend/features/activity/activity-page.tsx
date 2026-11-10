"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { listActivity } from "@/lib/api/activity";
import { apiErrorMessage } from "@/lib/api/client";
import type { ActivityEvent } from "@/lib/api/types";
import { paginate } from "@/lib/pagination";
import { ActivityDetailDrawer } from "./activity-detail-drawer";
import { formatActivityEvent, formatActivityWhen } from "./format";

export const ACTIVITY_PAGE_SIZE = 15;
const FETCH_LIMIT = 200;

async function loadActivity(): Promise<ActivityEvent[]> {
  const all: ActivityEvent[] = [];
  const seen = new Set<number>();
  let offset = 0;

  for (let page = 0; page < 25; page += 1) {
    const rows = await listActivity({ limit: FETCH_LIMIT, offset });
    let added = 0;
    for (const row of rows) {
      if (seen.has(row.id)) continue;
      seen.add(row.id);
      all.push(row);
      added += 1;
    }
    if (rows.length < FETCH_LIMIT || added === 0) break;
    offset += rows.length;
  }

  all.sort((a, b) => b.id - a.id);
  return all;
}

export function ActivityPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idParam = searchParams.get("id");
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [dismissedId, setDismissedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loadActivity()
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
  }, [reloadKey]);

  const activeId = idParam && idParam !== dismissedId ? idParam : null;
  const selected = events.find((event) => String(event.id) === activeId) ?? null;
  const missingHighlight = Boolean(activeId) && !loading && !error && !selected;

  useEffect(() => {
    if (!activeId) return;
    const index = events.findIndex((event) => String(event.id) === activeId);
    if (index < 0) return;
    setPage(Math.floor(index / ACTIVITY_PAGE_SIZE) + 1);
  }, [activeId, events]);

  const pageCount = Math.max(1, Math.ceil(events.length / ACTIVITY_PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const paged = paginate(events, safePage, ACTIVITY_PAGE_SIZE);

  useEffect(() => {
    if (!activeId) return;
    document.getElementById(`activity-${activeId}`)?.scrollIntoView({ block: "nearest" });
  }, [activeId, safePage, events]);

  function openEvent(event: ActivityEvent) {
    setDismissedId(null);
    router.replace(`/activity?id=${encodeURIComponent(String(event.id))}`, { scroll: false });
  }

  function closeDrawer() {
    if (idParam) setDismissedId(idParam);
    router.replace("/activity", { scroll: false });
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">
            Activity
          </p>
          <h1
            className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            What the agent did
          </h1>
          <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
            Chat, task, approval, and connection events in one timeline.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setReloadKey((key) => key + 1)}
          disabled={loading}
        >
          Refresh
        </Button>
      </header>

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-[var(--muted)]">
          <Spinner size="sm" />
          Loading activity…
        </div>
      ) : null}

      {!loading && error ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
          <Button variant="secondary" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
            Try again
          </Button>
        </div>
      ) : null}

      {!loading && !error && missingHighlight ? (
        <p className="text-sm text-[var(--muted)]" role="status">
          That activity entry is not in the loaded timeline.
        </p>
      ) : null}

      {!loading && !error && events.length === 0 ? (
        <EmptyState
          title="No activity yet"
          description="Actions from chat and tasks will land here."
        />
      ) : null}

      {!loading && !error && events.length > 0 ? (
        <>
          <ul className="flex flex-col gap-2">
            {paged.items.map((event) => {
              const highlighted = String(event.id) === activeId;
              return (
                <li key={event.id}>
                  <button
                    type="button"
                    id={`activity-${event.id}`}
                    onClick={() => openEvent(event)}
                    aria-current={highlighted ? "true" : undefined}
                    className={`w-full rounded-[var(--radius)] border px-4 py-3 text-left transition hover:bg-[var(--canvas)] ${
                      highlighted
                        ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                        : "border-[var(--border)] bg-[var(--surface)]"
                    }`}
                  >
                    <span className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="text-sm font-medium text-[var(--ink)]">
                        {formatActivityEvent(event.event)}
                      </span>
                      <time className="text-xs text-[var(--muted)]" dateTime={event.occurred_at}>
                        {formatActivityWhen(event.occurred_at)}
                      </time>
                    </span>
                    <span className="mt-1 block text-xs text-[var(--muted)]">{event.actor}</span>
                  </button>
                </li>
              );
            })}
          </ul>
          <Pagination
            page={paged.page}
            pageSize={paged.pageSize}
            total={paged.total}
            onPageChange={setPage}
          />
        </>
      ) : null}

      <ActivityDetailDrawer event={selected} open={selected !== null} onClose={closeDrawer} />
    </div>
  );
}
