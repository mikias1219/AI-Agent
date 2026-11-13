"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
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

function startOfWeek(d: Date): Date {
  const day = new Date(d);
  day.setHours(0, 0, 0, 0);
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

export function CalendarPage() {
  const router = useRouter();
  const [status, setStatus] = useState<GoogleStatus | null>(null);
  const [events, setEvents] = useState<GoogleEvent[]>([]);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const connected = Boolean(status?.connected && status.services.calendar);
  const weekLabel = `${dayLabel(days[0]!)} – ${dayLabel(days[6]!)}`;
  const today = new Date();

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2
            className="text-2xl font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Calendar
          </h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Your week, read from a connected Google Calendar.
          </p>
        </div>
        {connected ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setWeekStart((prev) => addDays(prev, -7))}
            >
              Previous
            </Button>
            <span className="text-sm text-[var(--muted)]">{weekLabel}</span>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setWeekStart((prev) => addDays(prev, 7))}
            >
              Next
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setWeekStart(startOfWeek(new Date()))}
            >
              This week
            </Button>
            <Button
              type="button"
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

      {!loading && !error && connected ? (
        <div className="grid gap-3 md:grid-cols-7">
          {days.map((day) => {
            const items = byDay.get(day.toDateString()) ?? [];
            const isToday = sameDay(day, today);
            return (
              <section
                key={day.toISOString()}
                className={`flex min-h-40 flex-col gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3 ${
                  isToday ? "ring-1 ring-[var(--accent)]" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-1">
                  <h3 className="text-xs font-medium text-[var(--muted)]">{dayLabel(day)}</h3>
                  {isToday ? <StatusChip tone="accent">Today</StatusChip> : null}
                </div>
                {items.length === 0 ? (
                  <p className="text-xs text-[var(--muted)]">No events</p>
                ) : (
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
                )}
              </section>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
