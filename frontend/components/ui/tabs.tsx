"use client";

export type TabItem = { id: string; label: string };

export type TabsProps = {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
};

export function Tabs({ items, value, onChange }: TabsProps) {
  return (
    <div
      role="tablist"
      aria-orientation="horizontal"
      className="flex flex-wrap gap-1 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-1"
    >
      {items.map((item) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={selected}
            id={`tab-${item.id}`}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
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
  );
}
