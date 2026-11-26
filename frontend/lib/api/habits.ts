import { api } from "./client";

export type Recurrence = {
  freq: "daily" | "weekly" | "monthly" | "quarterly" | "yearly";
  interval?: number;
  weekdays?: number[];
  day_of_month?: number | null;
  start?: string | null;
  end?: string | null;
};

export type HabitStreak = {
  current: number;
  best: number;
  done_last_7: number;
  due_last_7: number;
  done_last_30: number;
  due_last_30: number;
};

export type Habit = {
  id: string;
  name: string;
  kind: string;
  rule: Recurrence;
  target_value: number | null;
  target_unit: string;
  icon: string;
  archived: boolean;
  counts_toward_score: boolean;
  streak?: HabitStreak | null;
};

export type HabitCheckState = "open" | "done" | "skipped";

export type HabitToday = {
  day: string;
  items: (Habit & { status: HabitCheckState; value: number | null })[];
  done: number;
  due: number;
  rate: number | null;
};

export type HabitGrid = {
  from: string;
  to: string;
  rows: { habit: Habit; cells: { day: string; state: HabitCheckState | "off" }[] }[];
};

export type CreateHabitInput = {
  name: string;
  rule: Recurrence;
  kind?: string;
  target_value?: number;
  target_unit?: string;
};

export const listHabits = () => api<Habit[]>("/habits");
export const getHabitsToday = () => api<HabitToday>("/habits/today");
export const getHabitGrid = (days = 7) => api<HabitGrid>(`/habits/grid?days=${days}`);

export const createHabit = (input: CreateHabitInput) =>
  api<Habit>("/habits", { method: "POST", body: JSON.stringify(input) });

export const archiveHabit = (id: string) =>
  api<unknown>(`/habits/${encodeURIComponent(id)}`, { method: "DELETE" }).catch(() => undefined);

export const checkInHabit = (
  id: string,
  body: { status?: "done" | "skipped"; note?: string; value?: number; day?: string } = {},
) =>
  api<unknown>(`/habits/${encodeURIComponent(id)}/checkins`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const undoHabitCheckIn = (id: string, day: string) =>
  api<unknown>(`/habits/${encodeURIComponent(id)}/checkins/${day}`, {
    method: "DELETE",
  }).catch(() => undefined);

/** Plain-language schedules shared by habits and recurring tasks. */
export const SCHEDULE_CHOICES: { id: string; label: string; rule: Recurrence }[] = [
  { id: "daily", label: "Every day", rule: { freq: "daily" } },
  { id: "weekdays", label: "Weekdays", rule: { freq: "weekly", weekdays: [0, 1, 2, 3, 4] } },
  { id: "weekly", label: "Once a week", rule: { freq: "weekly" } },
  { id: "monthly", label: "Once a month", rule: { freq: "monthly" } },
];

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** "Every day", "Mon, Wed, Fri", "Every 2 weeks", "Monthly on day 31". */
export function describeRule(rule: Recurrence): string {
  const n = rule.interval && rule.interval > 1 ? rule.interval : 1;
  if (rule.freq === "daily") return n === 1 ? "Every day" : `Every ${n} days`;
  if (rule.freq === "weekly") {
    const days = (rule.weekdays ?? []).map((d) => WEEKDAYS[d]).join(", ");
    const base = n === 1 ? "Weekly" : `Every ${n} weeks`;
    return days ? `${base}: ${days}` : base;
  }
  if (rule.freq === "monthly")
    return `${n === 1 ? "Monthly" : `Every ${n} months`}${rule.day_of_month ? ` on day ${rule.day_of_month}` : ""}`;
  if (rule.freq === "quarterly") return "Every quarter";
  return "Every year";
}
