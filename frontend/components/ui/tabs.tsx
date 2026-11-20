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
};

export function Tabs({ items, value, onChange, panels, "aria-label": ariaLabel }: TabsProps) {
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
        className="flex w-fit flex-wrap gap-1 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-1"
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
              className={`rounded-lg px-3 py-2 text-[length:var(--text-body)] font-medium transition ${
                selected
                  ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "text-[var(--muted)] hover:bg-[var(--canvas)] hover:text-[var(--ink)]"
              }`}
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
