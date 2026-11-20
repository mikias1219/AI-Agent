import { cacheKey, cachedFetch, invalidatePrefix } from "@/lib/client-cache/cache";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${API_BASE}/api${path}`;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function rawApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    credentials: "include",
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    body: options.body === undefined ? undefined : (options.body as BodyInit),
  });
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    throw new ApiError("The backend returned an unreadable response.", response.status);
  }
  if (!response.ok) {
    const detail = (data as { detail?: string | { msg: string }[] })?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg).join(". ")
      : typeof detail === "string"
        ? detail
        : `Request failed (${response.status}).`;
    throw new ApiError(message, response.status);
  }
  return data as T;
}

export type ApiOptions = RequestInit & {
  /** Skip GET cache/dedupe for this call. */
  bypassCache?: boolean;
  /** Override GET cache TTL (ms). */
  cacheTtlMs?: number;
};

/**
 * JSON API helper. GETs are deduped and briefly cached; non-GETs invalidate related keys.
 */
export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { bypassCache, cacheTtlMs, ...init } = options;
  const method = (init.method || "GET").toUpperCase();
  if (method !== "GET") {
    const result = await rawApi<T>(path, init);
    // Broad invalidation so shell badges and lists refresh after mutations.
    invalidatePrefix("GET:");
    return result;
  }
  const key = cacheKey(path, init);
  return cachedFetch(key, () => rawApi<T>(path, init), {
    ttlMs: cacheTtlMs,
    bypass: bypassCache,
  });
}

export function apiErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error && err.name !== "AbortError") return err.message;
  return "Something went wrong. Try again.";
}
