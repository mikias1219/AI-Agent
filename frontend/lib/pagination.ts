export function paginate<T>(
  items: T[],
  page: number,
  pageSize: number,
): { items: T[]; total: number; page: number; pageSize: number } {
  const total = items.length;
  const safePage = Math.max(1, page);
  const safePageSize = Math.max(1, pageSize);
  const start = (safePage - 1) * safePageSize;

  return {
    items: items.slice(start, start + safePageSize),
    total,
    page: safePage,
    pageSize: safePageSize,
  };
}
