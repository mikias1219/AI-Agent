import { api } from "./client";
import type { ActivityEvent } from "./types";

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
