import type { MoneyRow } from "./finance";
import type { HabitToday } from "./habits";
import { api } from "./client";
import type { DaySummary } from "./days";
import type { Goal } from "./goals";
import type { OnboardingState } from "./onboarding";

export type TodayNeedsYouItem = {
  kind: "approval" | "suggestion";
  id: string;
  run_id?: string | null;
  tool_name?: string;
  summary: string;
  /** Suggestions only: why, and the required citation. */
  reason?: string;
  source?: string;
  urgency?: number;
  risk?: string;
  untrusted_content?: boolean;
  created_at?: string | null;
  expires_at?: string | null;
};

export type TodayEvent = {
  id: string;
  title: string;
  startsAt: string;
  location?: string;
};

export type TodayActiveRun = {
  id: string;
  status: "running" | "awaiting_approval" | string;
  origin: string;
  input: string;
  created_at: string | null;
};

export type TodayPlanTask = {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_at: string | null;
  plan_date?: string | null;
  project: string | null;
};

export type TodayConnectionWarning = {
  id: string;
  severity: "info" | "warning" | "error" | string;
  message: string;
  action?: { label: string; href: string } | null;
};

export type TodayBriefingItem = {
  title: string;
  time?: string | null;
  detail?: string | null;
};

/** `status` mirrors BriefingSection.status: ok | empty | not_connected | unavailable | error. */
export type TodayBriefingSection = {
  id: string;
  heading: string;
  status: string;
  summary: string;
  items: TodayBriefingItem[];
};

export type TodayBriefing = {
  text: string | null;
  summary: string | null;
  sections: TodayBriefingSection[];
  run_id: string | null;
  sources?: Record<string, string>;
  model?: string;
  prompt_version?: string;
};

export type TodayLife = {
  learn?: { due: number; total: number; next_term: string | null };
  reading?: {
    next: string | null;
    plan_name: string | null;
    read_today: boolean;
    streak_days: number;
  };
  diary?: { wrote_today: boolean; streak_days: number };
  notes?: { recent: { id: string; title: string; updated_at: string }[] };
};

export type TodayDay = {
  date: string;
  summary: DaySummary;
  next_task: { id: string; title: string; due_at: string | null } | null;
};

export type TodayPayload = {
  greeting: { name: string; summary: string | null };
  needs_you: TodayNeedsYouItem[];
  now_next: {
    events: TodayEvent[];
    calendar_connected: boolean;
    active_run: TodayActiveRun | null;
  };
  /** `tasks` are on today; `overdue` are open tasks from earlier days (same day rule as Plan). */
  plan: { tasks: TodayPlanTask[]; overdue?: TodayPlanTask[]; plan_id: string | null };
  goals: Goal[];
  since_last_looked: unknown[];
  onboarding: OnboardingState;
  connections: { warnings: TodayConnectionWarning[] };
  briefing: TodayBriefing;
  /** Absent until the owner has used notes, diary, learning or reading. */
  life?: TodayLife | null;
  /** Always present per contract; treat defensively. */
  day?: TodayDay | null;
  /** Habits due today and the money row; absent if that module failed to load. */
  habits?: HabitToday | null;
  money?: MoneyRow | null;
};

export async function getToday(): Promise<TodayPayload> {
  return api<TodayPayload>("/today");
}
