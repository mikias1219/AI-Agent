/** The API serves at most this many rows per request (see docs/LIFE_API_CONTRACT.md). */
export const API_PAGE_LIMIT = 200;

/**
 * Load a whole list in API-sized pages, newest first, up to `max` rows.
 * `fetchPage` receives the page size and offset to request.
 */
export async function fetchAllPages<T>(
  fetchPage: (limit: number, offset: number) => Promise<T[]>,
  max = 2000,
): Promise<T[]> {
  const rows: T[] = [];
  while (rows.length < max) {
    const limit = Math.min(API_PAGE_LIMIT, max - rows.length);
    const page = await fetchPage(limit, rows.length);
    rows.push(...page);
    if (page.length < limit) break;
  }
  return rows;
}

/** One request never asks for more than the API allows. */
export function clampLimit(limit: number): number {
  return Math.max(1, Math.min(API_PAGE_LIMIT, Math.floor(limit)));
}
