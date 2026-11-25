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

export type LearnKind = "word" | "phrase" | "fact";
export type ReviewResult = "know" | "again";

export type LearnItem = {
  id: string;
  kind: LearnKind;
  term: string;
  meaning: string;
  example: string;
  language: string;
  topic: string;
  box: number;
  next_review_at: string;
  times_correct: number;
  times_wrong: number;
  created_at: string;
  updated_at: string;
};

export type LearnStats = {
  total: number;
  due: number;
  learned: number;
  streak_days: number;
  reviewed_today: number;
};

export type LearnItemInput = {
  kind?: LearnKind;
  term: string;
  meaning: string;
  example: string;
  language: string;
  topic: string;
};

export type ListLearnParams = {
  q?: string;
  topic?: string;
  language?: string;
  due?: boolean;
  limit?: number;
  offset?: number;
};

export function listLearnItems(params: ListLearnParams = {}): Promise<LearnItem[]> {
  const page = (limit: number, offset: number) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.topic) qs.set("topic", params.topic);
    if (params.language) qs.set("language", params.language);
    if (params.due) qs.set("due", "true");
    qs.set("limit", String(limit));
    qs.set("offset", String(offset));
    return api<LearnItem[]>(`/learn/items?${qs.toString()}`);
  };
  // An explicit limit is one request; otherwise load the whole list in API-sized pages.
  if (params.limit !== undefined) return page(clampLimit(params.limit), params.offset ?? 0);
  return fetchAllPages(page);
}

export function createLearnItem(input: LearnItemInput): Promise<LearnItem[]> {
  return api<LearnItem[]>("/learn/items", { method: "POST", body: JSON.stringify(input) });
}

export function updateLearnItem(id: string, patch: Partial<LearnItemInput>): Promise<LearnItem> {
  return api<LearnItem>(`/learn/items/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteLearnItem(id: string): Promise<void> {
  return del204(`/learn/items/${encodeURIComponent(id)}`, "word");
}

export function reviewLearnItem(id: string, result: ReviewResult): Promise<LearnItem> {
  return api<LearnItem>(`/learn/items/${encodeURIComponent(id)}/review`, {
    method: "POST",
    body: JSON.stringify({ result }),
  });
}

export function getLearnStats(): Promise<LearnStats> {
  return api<LearnStats>("/learn/stats", { bypassCache: true });
}

export function listLearnTopics(): Promise<string[]> {
  return api<string[]>("/learn/topics");
}
