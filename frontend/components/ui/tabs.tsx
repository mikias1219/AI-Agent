"use client";

import { useId, type KeyboardEvent, type ReactNode } from "react";

export type TabItem = { id: string; label: string };

export type TabsProps = {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  /** Optional panels keyed by tab id. When set, a matching tabpanel is rendered. */
  panels?: Record<string, ReactNode>;
  "aria-label"?: string;
  /** "quiet" = small pill filters under a page's main tabs, so two rows don't compete. */
  variant?: "default" | "quiet";
};

export function Tabs({
  items,
  value,
  onChange,
  panels,
  "aria-label": ariaLabel,
  variant = "default",
}: TabsProps) {
  const quiet = variant === "quiet";
  const baseId = useId();

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = items.findIndex((item) => item.id === value);
    if (index < 0) return;
    let next = index;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      next = (index + 1) % items.length;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      next = (index - 1 + items.length) % items.length;
    } else if (event.key === "Home") {
      next = 0;
    } else if (event.key === "End") {
      next = items.length - 1;
    } else {
      return;
    }
    event.preventDefault();
    const id = items[next]?.id;
    if (id) onChange(id);
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        role="tablist"
        aria-label={ariaLabel}
        aria-orientation="horizontal"
        className={
          quiet
            ? "flex w-fit max-w-full flex-nowrap gap-1.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            : "flex w-fit max-w-full flex-nowrap gap-1 overflow-x-auto rounded-[var(--radius)] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden border border-[var(--border)] bg-[var(--subtle)] p-1"
        }
        onKeyDown={onKeyDown}
      >
        {items.map((item) => {
          const selected = item.id === value;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`${baseId}-tab-${item.id}`}
              aria-selected={selected}
              aria-controls={panels ? `${baseId}-panel-${item.id}` : undefined}
              tabIndex={selected ? 0 : -1}
              className={
                quiet
                  ? `min-h-8 shrink-0 whitespace-nowrap rounded-full border px-3 py-1 text-[length:var(--text-small)] font-medium transition-colors duration-150 motion-reduce:transition-none ${
                      selected
                        ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                        : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--ink)]"
                    }`
                  : `min-h-9 shrink-0 whitespace-nowrap rounded-[var(--radius-sm)] px-3 py-1.5 text-[length:var(--text-body)] font-medium transition-[background-color,color,box-shadow] duration-150 motion-reduce:transition-none ${
                      selected
                        ? "bg-[var(--surface)] text-[var(--accent-strong)] shadow-[var(--shadow-1)] ring-1 ring-[var(--border)]"
                        : "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--ink)]"
                    }`
              }
              onClick={() => onChange(item.id)}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {panels
        ? items.map((item) => {
            const selected = item.id === value;
            return (
              <div
                key={item.id}
                role="tabpanel"
                id={`${baseId}-panel-${item.id}`}
                aria-labelledby={`${baseId}-tab-${item.id}`}
                hidden={!selected}
              >
                {selected ? panels[item.id] : null}
              </div>
            );
          })
        : null}
    </div>
  );
}
