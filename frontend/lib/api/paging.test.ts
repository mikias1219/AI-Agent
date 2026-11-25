import { describe, expect, it } from "vitest";
import { API_PAGE_LIMIT, clampLimit, fetchAllPages } from "./paging";

function source(total: number) {
  const calls: Array<[number, number]> = [];
  const fetchPage = async (limit: number, offset: number) => {
    calls.push([limit, offset]);
    return Array.from(
      { length: Math.max(0, Math.min(limit, total - offset)) },
      (_, i) => offset + i,
    );
  };
  return { calls, fetchPage };
}

describe("fetchAllPages", () => {
  it("never requests more than the API allows", async () => {
    const { calls, fetchPage } = source(450);
    const rows = await fetchAllPages(fetchPage);
    expect(rows).toHaveLength(450);
    expect(calls.every(([limit]) => limit <= API_PAGE_LIMIT)).toBe(true);
    expect(calls.map(([, offset]) => offset)).toEqual([0, 200, 400]);
  });

  it("stops after a short page and does not ask again", async () => {
    const { calls, fetchPage } = source(5);
    expect(await fetchAllPages(fetchPage)).toHaveLength(5);
    expect(calls).toHaveLength(1);
  });

  it("returns an empty list for an empty source", async () => {
    const { fetchPage } = source(0);
    expect(await fetchAllPages(fetchPage)).toEqual([]);
  });

  it("stops at the ceiling", async () => {
    const { fetchPage } = source(10_000);
    expect(await fetchAllPages(fetchPage, 450)).toHaveLength(450);
  });
});

describe("clampLimit", () => {
  it("keeps a single request inside 1..200", () => {
    expect(clampLimit(500)).toBe(200);
    expect(clampLimit(0)).toBe(1);
    expect(clampLimit(50.7)).toBe(50);
  });
});
