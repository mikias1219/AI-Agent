import { api } from "./client";

export type Automation = {
  id: string;
  kind: string;
  enabled: boolean;
  schedule_time: string;
  channels: string[];
  last_run_at: string | null;
  last_result: string;
  last_run_id: string | null;
};

export type Reminder = {
  id: string;
  text: string;
  remind_at: string | null;
  task_id: string | null;
  channels: string[];
  status: string;
  late: boolean;
  delivered_at: string | null;
  created_at: string | null;
};

export async function listAutomations(): Promise<Automation[]> {
  return api<Automation[]>("/automations");
}

export async function patchAutomation(
  id: string,
  input: { enabled?: boolean; schedule_time?: string; channels?: string[] },
): Promise<Automation> {
  return api<Automation>(`/automations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function runAutomation(
  id: string,
): Promise<{ processed: number; automation: Automation | null }> {
  return api(`/automations/${id}/run`, { method: "POST", body: "{}" });
}

export async function listReminders(status?: string): Promise<Reminder[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return api<Reminder[]>(`/reminders${qs}`);
}

export async function createReminder(input: {
  text: string;
  remind_at: string;
  channels?: string[];
}): Promise<Reminder> {
  return api<Reminder>("/reminders", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export type BriefingSection = {
  id: string;
  heading: string;
  status: string;
  summary: string;
  items: { title: string; time?: string | null; detail?: string | null }[];
};

export type LatestBriefing = {
  text: string | null;
  summary?: string;
  sections?: BriefingSection[];
  sources?: Record<string, string>;
  run_id?: string | null;
  model?: string;
  prompt_version?: string;
};

export async function latestBriefing(): Promise<LatestBriefing> {
  return api("/briefing/latest");
}
