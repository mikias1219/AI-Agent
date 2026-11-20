/**
 * Tiny in-memory GET cache with in-flight dedupe (Phase 6 data layer).
 * Mutations should call `invalidate` / `invalidatePrefix` so UI stays truthful.
 */

type Entry<T> = {
  value: T;
  expiresAt: number;
};

const store = new Map<string, Entry<unknown>>();
const inflight = new Map<string, Promise<unknown>>();

const DEFAULT_TTL_MS = 2_500;

export function cacheKey(path: string, init?: RequestInit): string {
  const method = (init?.method || "GET").toUpperCase();
  return `${method}:${path}`;
}

export function getCached<T>(key: string): T | undefined {
  const hit = store.get(key);
  if (!hit) return undefined;
  if (Date.now() > hit.expiresAt) {
    store.delete(key);
    return undefined;
  }
  return hit.value as T;
}

export function setCached<T>(key: string, value: T, ttlMs = DEFAULT_TTL_MS): void {
  store.set(key, { value, expiresAt: Date.now() + ttlMs });
}

export function invalidate(key: string): void {
  store.delete(key);
  inflight.delete(key);
}

export function invalidatePrefix(prefix: string): void {
  for (const key of store.keys()) {
    if (key.includes(prefix)) store.delete(key);
  }
  for (const key of inflight.keys()) {
    if (key.includes(prefix)) inflight.delete(key);
  }
}

export function clearCache(): void {
  store.clear();
  inflight.clear();
}

/** Deduplicate concurrent identical GETs; optional short TTL for shell polling. */
export async function cachedFetch<T>(
  key: string,
  loader: () => Promise<T>,
  options?: { ttlMs?: number; bypass?: boolean },
): Promise<T> {
  if (!options?.bypass) {
    const hit = getCached<T>(key);
    if (hit !== undefined) return hit;
    const pending = inflight.get(key) as Promise<T> | undefined;
    if (pending) return pending;
  }
  const promise = loader()
    .then((value) => {
      setCached(key, value, options?.ttlMs ?? DEFAULT_TTL_MS);
      return value;
    })
    .finally(() => {
      inflight.delete(key);
    });
  inflight.set(key, promise);
  return promise;
}
