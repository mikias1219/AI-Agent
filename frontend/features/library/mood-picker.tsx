"use client";

import { Frown, Meh, Smile, SmilePlus, CloudRain, type LucideIcon } from "lucide-react";
import type { Mood } from "@/lib/api/notes";
import { MOODS } from "./library-logic";

const ICONS: Record<Mood, LucideIcon> = {
  great: SmilePlus,
  good: Smile,
  okay: Meh,
  low: Frown,
  bad: CloudRain,
};

export function MoodPicker({
  value,
  onChange,
}: {
  value: Mood | null;
  onChange: (m: Mood | null) => void;
}) {
  return (
    <div role="group" aria-label="Mood" className="flex flex-wrap gap-2">
      {MOODS.map((m) => {
        const Icon = ICONS[m.value];
        const on = value === m.value;
        return (
          <button
            key={m.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(on ? null : m.value)}
            className={`inline-flex min-h-11 items-center gap-1.5 rounded-full border px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-[var(--accent)] sm:min-h-9 ${
              on
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--ink)]"
            }`}
          >
            <Icon className="h-4 w-4" aria-hidden />
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
