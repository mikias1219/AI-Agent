import { api, apiUrl } from "./client";
import type { ActivityEvent, RunDetail } from "./types";

export type ActivityQuery = {
  limit?: number;
  offset?: number;
};

export async function listActivity(query: ActivityQuery = {}): Promise<ActivityEvent[]> {
  const params = new URLSearchParams();
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  if (query.offset !== undefined) params.set("offset", String(query.offset));
  const qs = params.toString();
  return api<ActivityEvent[]>(`/activity${qs ? `?${qs}` : ""}`);
}

export function activityExportUrl(): string {
  return apiUrl("/activity/export.csv");
}

export async function getRunDetail(runId: string): Promise<RunDetail> {
  return api<RunDetail>(`/runs/${encodeURIComponent(runId)}`);
}
