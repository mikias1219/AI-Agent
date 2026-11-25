import { clampLimit, fetchAllPages } from "./paging";
import { invalidatePrefix } from "@/lib/client-cache/cache";
import { ApiError, api, apiUrl } from "./client";

async function del204(path: string, what: string): Promise<void> {
  const response = await fetch(apiUrl(path), { method: "DELETE", credentials: "include" });
  if (!response.ok && response.status !== 204) {
    throw new ApiError(`Could not delete ${what}.`, response.status);
  }
  invalidatePrefix("GET:");
}

export type ReadingPlan = {
  id: string;
  name: string;
  items: string[];
  position: number;
  active: boolean;
  created_at: string;
  updated_at: string;
  next: string | null;
  progress: number;
};

export type ReadingLog = {
  id: string;
  reference: string;
  read_on: string;
  reflection: string;
  plan_id: string | null;
  created_at: string;
};

export type ReadingTemplate = { id: string; name: string; description: string; count: number };

export type ReadingStats = {
  logs: number;
  streak_days: number;
  read_today: boolean;
  active_plan: ReadingPlan | null;
};

export function listReadingTemplates(): Promise<ReadingTemplate[]> {
  return api<ReadingTemplate[]>("/reading/templates");
}

export function listReadingPlans(): Promise<ReadingPlan[]> {
  return api<ReadingPlan[]>("/reading/plans", { bypassCache: true });
}

export function createReadingPlan(input: {
  name: string;
  items?: string[];
  template?: string;
}): Promise<ReadingPlan> {
  return api<ReadingPlan>("/reading/plans", { method: "POST", body: JSON.stringify(input) });
}

export function updateReadingPlan(
  id: string,
  patch: { name?: string; active?: boolean; position?: number },
): Promise<ReadingPlan> {
  return api<ReadingPlan>(`/reading/plans/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteReadingPlan(id: string): Promise<void> {
  return del204(`/reading/plans/${encodeURIComponent(id)}`, "plan");
}

export function advanceReadingPlan(
  id: string,
  reflection?: string,
): Promise<{ plan: ReadingPlan; log: ReadingLog }> {
  return api(`/reading/plans/${encodeURIComponent(id)}/advance`, {
    method: "POST",
    body: JSON.stringify(reflection ? { reflection } : {}),
  });
}

export function listReadingLogs(
  params: { plan_id?: string; limit?: number; offset?: number } = {},
): Promise<ReadingLog[]> {
  const page = (limit: number, offset: number) => {
    const qs = new URLSearchParams();
    if (params.plan_id) qs.set("plan_id", params.plan_id);
    qs.set("limit", String(limit));
    qs.set("offset", String(offset));
    return api<ReadingLog[]>(`/reading/logs?${qs.toString()}`, { bypassCache: true });
  };
  if (params.limit !== undefined) return page(clampLimit(params.limit), params.offset ?? 0);
  return fetchAllPages(page);
}

export function createReadingLog(input: {
  reference: string;
  read_on?: string;
  reflection?: string;
  plan_id?: string | null;
}): Promise<ReadingLog> {
  return api<ReadingLog>("/reading/logs", { method: "POST", body: JSON.stringify(input) });
}

export function updateReadingLog(
  id: string,
  patch: { reference?: string; read_on?: string; reflection?: string },
): Promise<ReadingLog> {
  return api<ReadingLog>(`/reading/logs/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteReadingLog(id: string): Promise<void> {
  return del204(`/reading/logs/${encodeURIComponent(id)}`, "log entry");
}

export function getReadingStats(): Promise<ReadingStats> {
  return api<ReadingStats>("/reading/stats", { bypassCache: true });
}
