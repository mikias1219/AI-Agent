import { api } from "./client";

export type TimeEntry = {
  id: string;
  task_id: string | null;
  goal_id: string | null;
  project: string;
  note: string;
  started_at: string;
  ended_at: string | null;
  minutes: number;
  running: boolean;
  source: "timer" | "manual";
};

export type TimeSummary = {
  from: string;
  to: string;
  total_minutes: number;
  by_day: Record<string, number>;
  by_project: { project: string; minutes: number }[];
  by_task: { task_id: string; minutes: number }[];
};

export type TimeLink = { task_id?: string; project?: string; goal_id?: string; note?: string };

export const getRunningTimer = () => api<{ entry: TimeEntry | null }>("/time/running");
export const startTimer = (link: TimeLink = {}) =>
  api<TimeEntry>("/time/start", { method: "POST", body: JSON.stringify(link) });
export const stopTimer = () => api<TimeEntry>("/time/stop", { method: "POST", body: "{}" });
export const logTime = (body: TimeLink & { minutes: number; day?: string }) =>
  api<TimeEntry>("/time/entries", { method: "POST", body: JSON.stringify(body) });
export const listTimeEntries = (from?: string, to?: string) => {
  const query = new URLSearchParams();
  if (from) query.set("from", from);
  if (to) query.set("to", to);
  return api<TimeEntry[]>(`/time/entries?${query}`);
};
export const deleteTimeEntry = (id: string) =>
  api<unknown>(`/time/entries/${id}`, { method: "DELETE" }).catch(() => undefined);
export const getTimeSummary = (from?: string, to?: string) => {
  const query = new URLSearchParams();
  if (from) query.set("from", from);
  if (to) query.set("to", to);
  return api<TimeSummary>(`/time/summary?${query}`);
};

/** 135 → "2 h 15 min", 45 → "45 min". */
export function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}
