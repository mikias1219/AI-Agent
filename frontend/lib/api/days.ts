import { api } from "./client";
import type { Note } from "./notes";
import type { TaskOutcome, LifeTask } from "./tasks";

export type DaySummary = {
  planned: number;
  done: number;
  achieved: number;
  partial: number;
  missed: number;
  skipped: number;
  open: number;
  score: number | null;
};

export type DayEvent = { id: string; title: string; startsAt: string; location?: string };

export type DayReading = { id?: string; [key: string]: unknown };

export type Day = {
  date: string;
  is_today: boolean;
  tasks: LifeTask[];
  summary: DaySummary;
  events: DayEvent[];
  calendar_connected: boolean;
  diary: Note | null;
  readings: DayReading[];
  learned: { reviewed: number };
  /** Optional: set once the daily summary is backed up to Drive. */
  drive_url?: string | null;
};

export type DayRangeRow = {
  date: string;
  planned: number;
  achieved: number;
  partial: number;
  missed: number;
  skipped: number;
  open: number;
  score: number | null;
};

export type PeriodStats = {
  planned: number;
  achieved: number;
  partial: number;
  missed: number;
  rate: number | null;
};

export type DayStats = { streak_days: number; week: PeriodStats; month: PeriodStats };

export type CarryOverResult = { moved: number; to: string; task_ids: string[] };

export type { TaskOutcome };

export function getDay(date: string): Promise<Day> {
  return api<Day>(`/days/${encodeURIComponent(date)}`);
}

export function getDayRange(from: string, to: string): Promise<DayRangeRow[]> {
  const qs = new URLSearchParams({ from, to });
  return api<DayRangeRow[]>(`/days/range?${qs.toString()}`);
}

export function getDayStats(): Promise<DayStats> {
  return api<DayStats>("/days/stats");
}

export function carryOver(date: string, to?: string): Promise<CarryOverResult> {
  return api<CarryOverResult>(`/days/${encodeURIComponent(date)}/carry-over`, {
    method: "POST",
    body: JSON.stringify(to ? { to } : {}),
  });
}
