"use client";

import { useDensity, type Density } from "@/features/appearance/density-provider";

const OPTIONS: { id: Density; label: string }[] = [
  { id: "comfortable", label: "Comfortable" },
  { id: "compact", label: "Compact" },
];

export function DensityToggle({ className = "" }: { className?: string }) {
  const { density, setDensity } = useDensity();

  return (
    <div
      className={`inline-flex rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-0.5 ${className}`.trim()}
      role="group"
      aria-label="Density"
    >
      {OPTIONS.map((option) => {
        const active = density === option.id;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={active}
            onClick={() => setDensity(option.id)}
            className={`rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-xs font-medium transition ${
              active
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "text-[var(--muted)] hover:text-[var(--ink)]"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
