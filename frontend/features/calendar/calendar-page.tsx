"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button, buttonClassName } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { IconButton } from "@/components/ui/icon-button";
import { SkeletonRows } from "@/components/ui/skeleton";
import { ConnectPrompt } from "@/features/google/connect-prompt";
import {
  addDays,
  bucketWeek,
  dayKey,
  formatDayHeading,
  formatEventTime,
  isAllDay,
  parseStart,
  startOfDay,
} from "@/features/calendar/calendar-logic";
import { apiErrorMessage } from "@/lib/api/client";
import {
  getGoogleStatus,
  listCalendar,
  type GoogleEvent,
  type GoogleStatus,
} from "@/lib/api/google";

function chatHref(prompt: string): string {
  return `/chat?q=${encodeURIComponent(prompt)}`;
}

function startOfWeek(d: Date): Date {
  const day = startOfDay(d);
  return addDays(day, -((day.getDay() + 6) % 7)); // Monday first
}

type Part = "All day" | "Morning" | "Afternoon" | "Evening";

function partOf(event: GoogleEvent): Part {
  if (isAllDay(event.startsAt)) return "All day";
  const hour = parseStart(event.startsAt)?.getHours() ?? 0;
  if (hour < 12) return "Morning";
  if (hour < 17) return "Afternoon";
  return "Evening";
}

const PARTS: Part[] = ["All day", "Morning", "Afternoon", "Evening"];

export type CalendarPageProps = {
  embedded?: boolean;
};

export function CalendarPage(_props: CalendarPageProps = {}) {
  const [status, setStatus] = useState<GoogleStatus | null>(null);
  const [events, setEvents] = useState<GoogleEvent[]>([]);
  const [focusDay, setFocusDay] = useState(() => startOfDay(new Date()));
  const [openId, setOpenId] = useState<string | null>(null);
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
      const result = await listCalendar(1, 50);
      setEvents(result.items);
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

  const connected = Boolean(status?.connected && status.services.calendar);
  const weekStart = useMemo(() => startOfWeek(focusDay), [focusDay]);
  const week = useMemo(() => bucketWeek(events, weekStart), [events, weekStart]);
  const todayKey = dayKey(new Date());
  const focusKey = dayKey(focusDay);
  const focusBucket = week.days.find((d) => d.key === focusKey);
  const dayEvents = focusBucket?.events ?? [];
  const open = events.find((e) => e.id === openId) ?? null;
  const close = useCallback(() => setOpenId(null), []);

  const focusLabel = formatDayHeading(focusDay);
  const dayTitle = focusKey === todayKey ? `Today, ${focusLabel}` : focusLabel;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      {loading ? <SkeletonRows count={4} /> : null}

      {error ? (
        <div
          className="flex flex-col gap-3 rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--danger)_35%,var(--border))] bg-[color-mix(in_srgb,var(--danger)_8%,var(--surface))] px-4 py-3 text-sm text-[var(--danger)]"
          role="alert"
        >
          <p>Could not load your calendar. {error}</p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => void load()}>
              Try again
            </Button>
            {/401|expired|reconnect/i.test(error) ? (
              <Link href="/connections/google" className={buttonClassName("secondary")}>
                Reconnect Google
              </Link>
            ) : null}
          </div>
        </div>
      ) : null}

      {!loading && !error && !connected ? <ConnectPrompt noun="events" status={status} /> : null}

      {!loading && !error && connected ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <IconButton
              label="Previous week"
              className="min-h-11 min-w-11 sm:min-h-0 sm:min-w-0"
              onClick={() => setFocusDay((d) => addDays(d, -7))}
            >
              <ChevronLeft className="h-4 w-4" aria-hidden />
            </IconButton>
            <Button
              variant="secondary"
              className="min-h-11 sm:min-h-0"
              onClick={() => setFocusDay(startOfDay(new Date()))}
            >
              Today
            </Button>
            <IconButton
              label="Next week"
              className="min-h-11 min-w-11 sm:min-h-0 sm:min-w-0"
              onClick={() => setFocusDay((d) => addDays(d, 7))}
            >
              <ChevronRight className="h-4 w-4" aria-hidden />
            </IconButton>
            <Link
              href={chatHref("Create a calendar event. Ask me for the title and time.")}
              className={buttonClassName("primary", "md", "ml-auto min-h-11 sm:min-h-0")}
            >
              Create event
            </Link>
          </div>

          <ul className="grid grid-cols-7 gap-1" aria-label="This week">
            {week.days.map((day) => {
              const selected = day.key === focusKey;
              const count = day.events.length;
              return (
                <li key={day.key}>
                  <button
                    type="button"
                    aria-pressed={selected}
                    aria-label={`${formatDayHeading(day.date)}, ${count === 0 ? "no events" : `${count} event${count === 1 ? "" : "s"}`}`}
                    onClick={() => setFocusDay(day.date)}
                    className={`flex min-h-11 w-full flex-col items-center justify-center rounded-[var(--radius)] border px-1 py-1.5 text-xs transition focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${
                      selected
                        ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--canvas)]"
                    }`}
                  >
                    <span className="text-[var(--muted)]">
                      {new Intl.DateTimeFormat("en", { weekday: "narrow" }).format(day.date)}
                    </span>
                    <span className={day.key === todayKey ? "font-bold" : "font-medium"}>
                      {day.date.getDate()}
                    </span>
                    <span
                      aria-hidden
                      className={`mt-0.5 h-1.5 w-1.5 rounded-full ${
                        count > 0 ? "bg-[var(--accent)]" : "bg-transparent"
                      }`}
                    />
                  </button>
                </li>
              );
            })}
          </ul>

          <Card
            title={dayTitle}
            description={
              dayEvents.length === 0
                ? "Nothing scheduled in your calendar."
                : `${dayEvents.length} event${dayEvents.length === 1 ? "" : "s"} from Google Calendar.`
            }
          >
            {dayEvents.length === 0 ? (
              <EmptyState
                title="A free day"
                description="Nothing is booked. Ask AURA to block focus time or set something up."
                action={
                  <Link
                    href={chatHref("Find time for focus work on " + focusLabel + ".")}
                    className={buttonClassName()}
                  >
                    Find time
                  </Link>
                }
              />
            ) : (
              <div className="flex flex-col gap-4">
                {PARTS.map((part) => {
                  const items = dayEvents.filter((e) => partOf(e) === part);
                  if (items.length === 0) return null;
                  return (
                    <section key={part} aria-label={part}>
                      <h3 className="mb-1 text-xs font-medium tracking-wide text-[var(--muted)] uppercase">
                        {part}
                      </h3>
                      <ul className="divide-y divide-[var(--border)]">
                        {items.map((event) => (
                          <li key={event.id}>
                            <button
                              type="button"
                              onClick={() => setOpenId(event.id)}
                              className="flex min-h-11 w-full items-baseline gap-3 py-2.5 text-left transition hover:bg-[var(--canvas)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
                            >
                              <span className="w-16 shrink-0 text-xs text-[var(--muted)]">
                                {formatEventTime(event.startsAt)}
                              </span>
                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm font-medium text-[var(--ink)]">
                                  {event.title || "(untitled)"}
                                </span>
                                {event.location ? (
                                  <span className="block truncate text-xs text-[var(--muted)]">
                                    {event.location}
                                  </span>
                                ) : null}
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </section>
                  );
                })}
              </div>
            )}
          </Card>

          {week.later.length > 0 || week.days.every((d) => d.events.length === 0) ? (
            <p className="text-xs text-[var(--muted)]">
              {week.later.length > 0
                ? `${week.later.length} more event${week.later.length === 1 ? "" : "s"} after this week.`
                : "No events found this week."}
            </p>
          ) : null}
        </>
      ) : null}

      <Drawer open={open !== null} onClose={close} title={open?.title || "Event"}>
        {open ? (
          <div className="flex flex-col gap-4">
            <dl className="flex flex-col gap-2 text-sm">
              <div>
                <dt className="text-xs text-[var(--muted)]">When</dt>
                <dd className="text-[var(--ink)]">
                  {(() => {
                    const start = parseStart(open.startsAt);
                    return start
                      ? `${formatDayHeading(start)}, ${formatEventTime(open.startsAt)}`
                      : "Time not available";
                  })()}
                </dd>
              </div>
              {open.location ? (
                <div>
                  <dt className="text-xs text-[var(--muted)]">Where</dt>
                  <dd className="text-[var(--ink)]">{open.location}</dd>
                </div>
              ) : null}
            </dl>
            <div className="flex flex-col gap-2">
              <Link
                className={buttonClassName("primary", "md", "min-h-11")}
                href={chatHref(
                  `Find a better time for "${open.title}" on ${formatDayHeading(parseStart(open.startsAt) ?? new Date())}. Propose only real free slots.`,
                )}
              >
                Find time
              </Link>
              <Link
                className={buttonClassName("secondary", "md", "min-h-11")}
                href={chatHref("Create a calendar event. Ask me for the title and time.")}
              >
                Create event
              </Link>
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
