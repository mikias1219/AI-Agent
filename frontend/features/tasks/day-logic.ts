import type { LifeTask, TaskOutcome } from "@/lib/api/tasks";

const pad = (n: number) => String(n).padStart(2, "0");

/** `YYYY-MM-DD` in the browser's local time. */
export function toDateKey(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Parse `YYYY-MM-DD` as a local date at noon (safe across DST). Returns null when invalid. */
export function parseDateKey(key: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key);
  if (!m) return null;
  const date = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 12);
  return toDateKey(date) === key ? date : null;
}

export function addDays(key: string, days: number): string {
  const date = parseDateKey(key) ?? new Date();
  date.setDate(date.getDate() + days);
  return toDateKey(date);
}

/** Monday-first week of 7 date keys containing `key`. */
export function weekDates(key: string): string[] {
  const date = parseDateKey(key) ?? new Date();
  const offset = (date.getDay() + 6) % 7;
  const monday = addDays(toDateKey(date), -offset);
  return Array.from({ length: 7 }, (_, i) => addDays(monday, i));
}

/** The range to request for the week strip. */
export function weekRange(key: string): { from: string; to: string } {
  const days = weekDates(key);
  return { from: days[0], to: days[6] };
}

/** Day switching is limited to a sensible window around today. */
export const DAY_WINDOW_DAYS = 365;

export function clampDay(key: string, todayKey: string): string {
  const min = addDays(todayKey, -DAY_WINDOW_DAYS);
  const max = addDays(todayKey, DAY_WINDOW_DAYS);
  if (!parseDateKey(key)) return todayKey;
  if (key < min) return min;
  if (key > max) return max;
  return key;
}

export function canStep(key: string, delta: -1 | 1, todayKey: string): boolean {
  return clampDay(addDays(key, delta), todayKey) === addDays(key, delta);
}

export function dayHeading(key: string): { weekday: string; full: string } {
  const date = parseDateKey(key);
  if (!date) return { weekday: "", full: key };
  return {
    weekday: new Intl.DateTimeFormat("en", { weekday: "long" }).format(date),
    full: new Intl.DateTimeFormat("en", { month: "long", day: "numeric", year: "numeric" }).format(
      date,
    ),
  };
}

export function chipLabel(key: string): { weekday: string; day: string } {
  const date = parseDateKey(key);
  if (!date) return { weekday: "", day: key };
  return {
    weekday: new Intl.DateTimeFormat("en", { weekday: "short" }).format(date),
    day: String(date.getDate()),
  };
}

export function scorePercent(score: number | null | undefined): number | null {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  return Math.round(Math.max(0, Math.min(1, score)) * 100);
}

export function scoreWords(score: number | null | undefined): string {
  const pct = scorePercent(score);
  if (pct === null) return "No score yet";
  if (pct >= 80) return "Great day";
  if (pct >= 50) return "Solid";
  return "Tough day, try again tomorrow";
}

/** Suggest an outcome from what was done against the target. Owner may override. */
export function suggestOutcome(
  actual: number | null | undefined,
  target: number | null | undefined,
): TaskOutcome {
  if (!target || target <= 0 || actual === null || actual === undefined || Number.isNaN(actual)) {
    return "achieved";
  }
  if (actual >= target) return "achieved";
  if (actual > 0) return "partial";
  return "missed";
}

export const OUTCOME_LABEL: Record<TaskOutcome, string> = {
  achieved: "Achieved",
  partial: "Partly",
  missed: "Missed",
  skipped: "Skipped",
};

function num(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
}

/** Words for an outcome chip, e.g. "Achieved 30/30 push-ups", "Partly 18/30", "Missed". */
export function outcomeText(
  task: Pick<LifeTask, "outcome" | "actual_value" | "target_value" | "target_unit">,
): string | null {
  if (!task.outcome) return null;
  const label = OUTCOME_LABEL[task.outcome];
  const target = task.target_value;
  const actual = task.actual_value;
  if (task.outcome === "skipped" || !target || actual === null || actual === undefined) {
    return label;
  }
  const unit = task.outcome === "achieved" && task.target_unit ? ` ${task.target_unit}` : "";
  if (task.outcome === "partial") {
    return `${label} ${num(actual)}/${num(target)}${task.target_unit ? ` ${task.target_unit}` : ""}`;
  }
  if (task.outcome === "missed") return label;
  return `${label} ${num(actual)}/${num(target)}${unit}`;
}

export function targetText(task: Pick<LifeTask, "target_value" | "target_unit">): string | null {
  if (!task.target_value) return null;
  return `${num(task.target_value)}${task.target_unit ? ` ${task.target_unit}` : ""}`;
}

export function summaryLine(done: number, planned: number, score: number | null): string {
  const pct = scorePercent(score);
  return `Done ${done} of ${planned}${pct === null ? "" : `, score ${pct}%`}`;
}

/** True when a task is still open (not finished, not cancelled). */
export function isOpen(task: Pick<LifeTask, "status">): boolean {
  return task.status === "planned" || task.status === "in_progress" || task.status === "blocked";
}

/** Show the wrap-up link after 17:00 local with open tasks. */
export function showWrapUp(open: number, now: Date = new Date()): boolean {
  return open > 0 && now.getHours() >= 17;
}
