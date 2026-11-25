"use client";

import { useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { paginate } from "@/lib/pagination";
import { Button } from "./button";
import { EmptyState } from "./empty-state";
import { Pagination } from "./pagination";

export type Column<T> = {
  id: string;
  header: string;
  cell: (row: T) => ReactNode;
  /** Provide to make the column sortable. */
  sortValue?: (row: T) => string | number;
  align?: "left" | "right";
  /** Tailwind width class, e.g. "w-32". */
  width?: string;
  /** Hide below the md breakpoint. */
  hideOnMobile?: boolean;
};

export type DataTableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  /** Accessible table name. */
  label: string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  empty?: { title: string; description?: string };
  pageSize?: number;
  onRowClick?: (row: T) => void;
  /** Row currently open in a drawer. */
  selectedKey?: string | null;
  initialSort?: { id: string; dir: "asc" | "desc" };
};

type SortState = { id: string; dir: "asc" | "desc" } | null;

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  label,
  loading = false,
  error = null,
  onRetry,
  empty = { title: "Nothing here yet" },
  pageSize = 10,
  onRowClick,
  selectedKey = null,
  initialSort,
}: DataTableProps<T>) {
  const [sort, setSort] = useState<SortState>(initialSort ?? null);
  const [page, setPage] = useState(1);

  const sorted = useMemo(() => {
    const col = sort ? columns.find((c) => c.id === sort.id) : undefined;
    if (!sort || !col?.sortValue) return rows;
    const get = col.sortValue;
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = get(a);
      const y = get(b);
      return (x < y ? -1 : x > y ? 1 : 0) * factor;
    });
  }, [rows, columns, sort]);

  const view = paginate(sorted, page, pageSize);

  function toggle(id: string) {
    setPage(1);
    setSort((prev) =>
      prev?.id === id ? (prev.dir === "asc" ? { id, dir: "desc" } : null) : { id, dir: "asc" },
    );
  }

  if (error) {
    return (
      <div className="flex flex-wrap items-center gap-3 px-4 py-6 text-sm" role="alert">
        <span className="text-[var(--danger)]">
          Could not load {label.toLowerCase()}: {error}
        </span>
        {onRetry ? (
          <Button size="sm" variant="secondary" onClick={onRetry}>
            Try again
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse text-left text-[length:var(--text-body)]"
          aria-label={label}
          aria-busy={loading}
        >
          <thead>
            <tr className="border-y border-[var(--border)] bg-[var(--subtle)]">
              {columns.map((col) => {
                const dir = sort?.id === col.id ? sort.dir : null;
                const Icon = dir === "asc" ? ArrowUp : dir === "desc" ? ArrowDown : ChevronsUpDown;
                return (
                  <th
                    key={col.id}
                    scope="col"
                    aria-sort={
                      dir === "asc" ? "ascending" : dir === "desc" ? "descending" : undefined
                    }
                    className={`px-4 py-2.5 text-[length:var(--text-caption)] font-semibold tracking-[0.04em] text-[var(--muted)] uppercase ${
                      col.align === "right" ? "text-right" : ""
                    } ${col.width ?? ""} ${col.hideOnMobile ? "max-md:hidden" : ""}`.trim()}
                  >
                    {col.sortValue ? (
                      <button
                        type="button"
                        onClick={() => toggle(col.id)}
                        className="inline-flex items-center gap-1 rounded uppercase hover:text-[var(--ink)]"
                      >
                        {col.header}
                        <Icon
                          className={`h-3 w-3 ${dir ? "text-[var(--accent)]" : "opacity-50"}`}
                          aria-hidden
                        />
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: Math.min(pageSize, 5) }, (_, i) => (
                  <tr key={i} className="border-b border-[var(--border)]">
                    {columns.map((col) => (
                      <td
                        key={col.id}
                        className={`px-4 py-3 ${col.hideOnMobile ? "max-md:hidden" : ""}`}
                      >
                        <div
                          className="h-4 aura-shimmer rounded bg-[var(--subtle)]"
                          style={{ width: `${55 + ((i + col.id.length) % 4) * 10}%` }}
                        />
                      </td>
                    ))}
                  </tr>
                ))
              : view.items.map((row) => {
                  const key = rowKey(row);
                  const selected = selectedKey === key;
                  return (
                    <tr
                      key={key}
                      aria-selected={selected || undefined}
                      onClick={onRowClick ? () => onRowClick(row) : undefined}
                      onKeyDown={
                        onRowClick
                          ? (e) => {
                              if (
                                e.target === e.currentTarget &&
                                (e.key === "Enter" || e.key === " ")
                              ) {
                                e.preventDefault();
                                onRowClick(row);
                              }
                            }
                          : undefined
                      }
                      tabIndex={onRowClick ? 0 : undefined}
                      className={`min-h-[var(--row-min-h)] border-b border-[var(--border)] transition-colors duration-150 last:border-b-0 motion-reduce:transition-none ${
                        selected
                          ? "bg-[var(--accent-soft)]"
                          : onRowClick
                            ? "cursor-pointer hover:bg-[var(--hover)]"
                            : "hover:bg-[var(--hover)]"
                      }`}
                    >
                      {columns.map((col) => (
                        <td
                          key={col.id}
                          className={`px-4 py-[var(--row-pad-y)] align-middle ${
                            col.align === "right" ? "text-right" : ""
                          } ${col.hideOnMobile ? "max-md:hidden" : ""}`.trim()}
                        >
                          {col.cell(row)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </div>
      {!loading && rows.length === 0 ? (
        <div className="px-4 py-4">
          <EmptyState title={empty.title} description={empty.description} compact />
        </div>
      ) : null}
      {!loading && rows.length > pageSize ? (
        <div className="border-t border-[var(--border)] px-4 py-3">
          <Pagination
            page={view.page}
            pageSize={pageSize}
            total={view.total}
            onPageChange={setPage}
          />
        </div>
      ) : null}
    </div>
  );
}
