import type { ActivityEvent } from "@/lib/api/types";

export type DayBucket = {
  day: string;
  label: string;
  counts: Record<string, number>;
  total: number;
};

export type ActivityGroup =
  "completed" | "failed" | "approvals" | "routines" | "tasks" | "messages" | "other";

export const GROUP_LABELS: Record<ActivityGroup, string> = {
  completed: "Runs finished",
  failed: "Failed or stopped",
  approvals: "Approvals decided",
  routines: "Routines and reminders",
  tasks: "Tasks changed",
  messages: "Messages",
  other: "Other",
};

/** Chart series for every consumer, in stacking order. Colours are tokens, so dark mode works. */
export const ACTIVITY_SERIES: { key: ActivityGroup; label: string; color: string }[] = [
  { key: "completed", label: GROUP_LABELS.completed, color: "var(--chart-1)" },
  { key: "approvals", label: GROUP_LABELS.approvals, color: "var(--chart-2)" },
  { key: "routines", label: GROUP_LABELS.routines, color: "var(--chart-3)" },
  { key: "tasks", label: GROUP_LABELS.tasks, color: "var(--chart-4)" },
  { key: "messages", label: GROUP_LABELS.messages, color: "var(--chart-5)" },
  { key: "failed", label: GROUP_LABELS.failed, color: "var(--danger)" },
  { key: "other", label: GROUP_LABELS.other, color: "var(--muted)" },
];

/** System housekeeping, not something the agent did for the owner. Never counted. */
const HOUSEKEEPING_PREFIXES = [
  "telegram.runtime",
  "scheduler.tick",
  "onboarding.",
  "workspace.",
  "conversation.",
];

export function isHousekeeping(event: string): boolean {
  return HOUSEKEEPING_PREFIXES.some((prefix) => event.startsWith(prefix));
}

/** Maps an audit event name to one chart group. */
export function groupForEvent(event: string): ActivityGroup {
  if (event === "run.completed") return "completed";
  if (event === "run.failed" || event === "run.cancelled") return "failed";
  if (event.startsWith("approval.")) return "approvals";
  if (
    event.startsWith("automation.") ||
    event.startsWith("reminder.") ||
    event.startsWith("scheduler.")
  )
    return "routines";
  if (event.startsWith("task.")) return "tasks";
  if (event.startsWith("chat.") || event === "telegram.reply_sent") return "messages";
  return "other";
}

function dayKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** One bucket per local day for the last `days` days (oldest first), counted by group. */
export function bucketByDay(
  events: ActivityEvent[],
  days: number,
  now: Date = new Date(),
): DayBucket[] {
  const buckets: DayBucket[] = [];
  const index = new Map<string, DayBucket>();
  for (let i = days - 1; i >= 0; i -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
    const bucket: DayBucket = {
      day: dayKey(date),
      label: date.toLocaleDateString(undefined, { weekday: "short" }),
      counts: {},
      total: 0,
    };
    buckets.push(bucket);
    index.set(bucket.day, bucket);
  }
  for (const event of events) {
    const when = new Date(event.occurred_at);
    if (Number.isNaN(when.getTime())) continue;
    const bucket = index.get(dayKey(when));
    if (!bucket) continue;
    if (isHousekeeping(event.event)) continue;
    const group = groupForEvent(event.event);
    bucket.counts[group] = (bucket.counts[group] ?? 0) + 1;
    bucket.total += 1;
  }
  return buckets;
}

export type Breakdown = { key: string; label: string; value: number };

/** Total per group over the buckets, largest first, zero groups removed. */
export function breakdown(buckets: DayBucket[]): Breakdown[] {
  const totals = new Map<string, number>();
  for (const bucket of buckets) {
    for (const [key, value] of Object.entries(bucket.counts)) {
      totals.set(key, (totals.get(key) ?? 0) + value);
    }
  }
  return [...totals.entries()]
    .filter(([, value]) => value > 0)
    .map(([key, value]) => ({ key, label: GROUP_LABELS[key as ActivityGroup] ?? key, value }))
    .sort((a, b) => b.value - a.value);
}

/** Percent change of `current` against `previous`; null when there is no baseline. */
export function percentChange(current: number, previous: number): number | null {
  if (previous <= 0) return null;
  return Math.round(((current - previous) / previous) * 100);
}

export function sum(values: number[]): number {
  return values.reduce((a, b) => a + b, 0);
}
