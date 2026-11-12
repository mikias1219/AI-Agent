import type { GoogleEvent } from "@/lib/api/google";

export type DayBucket = {
  /** Local date key, YYYY-MM-DD. */
  key: string;
  date: Date;
  events: GoogleEvent[];
};

export function dayKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** An all-day event arrives as a bare date (no time). */
export function isAllDay(startsAt: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(startsAt);
}

export function parseStart(startsAt: string): Date | null {
  if (!startsAt) return null;
  // Bare dates are local all-day events; `new Date("2026-11-12")` would be UTC and shift the day.
  const date = isAllDay(startsAt) ? new Date(`${startsAt}T00:00:00`) : new Date(startsAt);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

/** Seven consecutive days from `from`, each with its events in start order. Events outside go to `later`. */
export function bucketWeek(
  events: GoogleEvent[],
  from: Date,
  days = 7,
): { days: DayBucket[]; later: GoogleEvent[]; undated: GoogleEvent[] } {
  const buckets: DayBucket[] = Array.from({ length: days }, (_, i) => {
    const date = addDays(startOfDay(from), i);
    return { key: dayKey(date), date, events: [] };
  });
  const byKey = new Map(buckets.map((b) => [b.key, b]));
  const windowEnd = addDays(startOfDay(from), days);
  const later: GoogleEvent[] = [];
  const undated: GoogleEvent[] = [];

  const sorted = [...events].sort((a, b) => {
    const da = parseStart(a.startsAt)?.getTime() ?? Number.POSITIVE_INFINITY;
    const db = parseStart(b.startsAt)?.getTime() ?? Number.POSITIVE_INFINITY;
    return da - db;
  });

  for (const event of sorted) {
    const start = parseStart(event.startsAt);
    if (!start) {
      undated.push(event);
      continue;
    }
    const bucket = byKey.get(dayKey(start));
    if (bucket) bucket.events.push(event);
    else if (start >= windowEnd) later.push(event);
    // Events before `from` are in the past and are not shown.
  }
  return { days: buckets, later, undated };
}

export function formatEventTime(startsAt: string): string {
  if (isAllDay(startsAt)) return "All day";
  const start = parseStart(startsAt);
  if (!start) return "";
  return new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(start);
}

export function formatDayHeading(date: Date): string {
  return new Intl.DateTimeFormat("en", { weekday: "short", month: "short", day: "numeric" }).format(
    date,
  );
}
