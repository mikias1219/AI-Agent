"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { StatusChip } from "@/components/ui/status-chip";
import { ConnectPrompt } from "@/features/google/connect-prompt";
import { apiErrorMessage } from "@/lib/api/client";
import {
  getGoogleStatus,
  listCalendar,
  type GoogleEvent,
  type GoogleStatus,
} from "@/lib/api/google";

type CalendarView = "week" | "day";

function startOfDay(d: Date): Date {
  const day = new Date(d);
  day.setHours(0, 0, 0, 0);
  return day;
}

function startOfWeek(d: Date): Date {
  const day = startOfDay(d);
  const weekday = (day.getDay() + 6) % 7; // Monday = 0
  day.setDate(day.getDate() - weekday);
  return day;
}

function addDays(d: Date, n: number): Date {
  const next = new Date(d);
  next.setDate(next.getDate() + n);
  return next;
}

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function dayLabel(d: Date): string {
  return new Intl.DateTimeFormat("en", { weekday: "short", month: "short", day: "numeric" }).format(
    d,
  );
}

function timeLabel(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(date);
}

function EventList({ items }: { items: GoogleEvent[] }) {
  if (items.length === 0) {
    return <p className="text-xs text-[var(--muted)]">No events</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {items.map((event) => (
        <li
          key={event.id}
          className="rounded-md border border-[var(--border)] bg-[var(--canvas)] px-2 py-1.5"
        >
          <p className="text-xs font-medium text-[var(--ink)]">{event.title}</p>
          <p className="text-[0.7rem] text-[var(--muted)]">
            {timeLabel(event.startsAt)}
            {event.location ? ` · ${event.location}` : ""}
          </p>
        </li>
      ))}
    </ul>
  );
}

export function CalendarPage() {
  const router = useRouter();
  const [status, setStatus] = useState<GoogleStatus | null>(null);
  const [events, setEvents] = useState<GoogleEvent[]>([]);
  const [view, setView] = useState<CalendarView>("week");
  const [focusDay, setFocusDay] = useState(() => startOfDay(new Date()));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const weekStart = useMemo(() => startOfWeek(focusDay), [focusDay]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextStatus = await getGoogleStatus();
      setStatus(nextStatus);
      if (!nextStatus.connected || !nextStatus.services.calendar) {
        setEvents([]);
        return;
      }
      const page = await listCalendar(1, 50);
      setEvents(page.items);
    } catch (err) {
      setError(apiErrorMessage(err));
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );

  const byDay = useMemo(() => {
    const map = new Map<string, GoogleEvent[]>();
    for (const day of days) {
      map.set(day.toDateString(), []);
    }
    for (const event of events) {
      const starts = new Date(event.startsAt);
      if (Number.isNaN(starts.getTime())) continue;
      const key = starts.toDateString();
      const bucket = map.get(key);
      if (bucket) bucket.push(event);
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.startsAt.localeCompare(b.startsAt));
    }
    return map;
  }, [days, events]);

  const dayEvents = useMemo(() => {
    const items = events
      .filter((event) => {
        const starts = new Date(event.startsAt);
        return !Number.isNaN(starts.getTime()) && sameDay(starts, focusDay);
      })
      .sort((a, b) => a.startsAt.localeCompare(b.startsAt));
    return items;
  }, [events, focusDay]);

  const connected = Boolean(status?.connected && status.services.calendar);
  const weekLabel = `${dayLabel(days[0]!)} – ${dayLabel(days[6]!)}`;
  const today = startOfDay(new Date());

  function goToday() {
    setFocusDay(startOfDay(new Date()));
  }

  function shift(daysDelta: number) {
    setFocusDay((prev) => addDays(prev, daysDelta));
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1
            className="text-2xl font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Calendar
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Events from your connected Google Calendar. AURA never invents slots.
          </p>
        </div>
        {connected ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="secondary" size="sm" onClick={goToday}>
              Today
            </Button>
            <div
              className="inline-flex rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-0.5"
              role="group"
              aria-label="Calendar view"
            >
              {(["week", "day"] as const).map((id) => {
                const active = view === id;
                return (
                  <button
                    key={id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setView(id)}
                    className={`rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-xs font-medium capitalize transition ${
                      active
                        ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "text-[var(--muted)] hover:text-[var(--ink)]"
                    }`}
                  >
                    {id}
                  </button>
                );
              })}
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => shift(view === "week" ? -7 : -1)}
            >
              Previous
            </Button>
            <span className="text-sm text-[var(--muted)]">
              {view === "week" ? weekLabel : dayLabel(focusDay)}
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => shift(view === "week" ? 7 : 1)}
            >
              Next
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() =>
                router.push(
                  `/chat?q=${encodeURIComponent("Find two hours of focus time this week.")}`,
                )
              }
            >
              Find time with AURA
            </Button>
          </div>
        ) : null}
      </header>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]" role="status">
          <Spinner />
          Loading calendar…
        </div>
      ) : null}

      {error ? (
        <div
          className="rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--danger)_35%,var(--border))] bg-[color-mix(in_srgb,var(--danger)_8%,var(--surface))] px-4 py-3 text-sm text-[var(--danger)]"
          role="alert"
        >
          {error}
          <Button type="button" variant="secondary" className="ml-3" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      ) : null}

      {!loading && !error && !connected ? <ConnectPrompt noun="events" status={status} /> : null}

      {!loading && !error && connected && view === "week" ? (
        <div className="grid gap-3 md:grid-cols-7">
          {days.map((day) => {
            const items = byDay.get(day.toDateString()) ?? [];
            const isToday = sameDay(day, today);
            const isFocus = sameDay(day, focusDay);
            return (
              <button
                key={day.toISOString()}
                type="button"
                onClick={() => {
                  setFocusDay(startOfDay(day));
                  setView("day");
                }}
                className={`flex min-h-40 flex-col gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3 text-left transition hover:border-[var(--accent)] ${
                  isToday || isFocus ? "ring-1 ring-[var(--accent)]" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-1">
                  <h3 className="text-xs font-medium text-[var(--muted)]">{dayLabel(day)}</h3>
                  {isToday ? <StatusChip tone="accent">Today</StatusChip> : null}
                </div>
                <EventList items={items} />
              </button>
            );
          })}
        </div>
      ) : null}

      {!loading && !error && connected && view === "day" ? (
        <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-[var(--ink)]">{dayLabel(focusDay)}</h2>
            {sameDay(focusDay, today) ? <StatusChip tone="accent">Today</StatusChip> : null}
          </div>
          {dayEvents.length === 0 ? (
            <EmptyState
              title="Nothing on this day"
              description="Ask AURA to find focus time — it will propose from real free slots only."
            />
          ) : (
            <EventList items={dayEvents} />
          )}
        </section>
      ) : null}
    </div>
  );
}
