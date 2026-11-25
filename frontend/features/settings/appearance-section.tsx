"use client";

import { Card } from "@/components/ui/card";
import { useTheme, type ThemePreference } from "@/features/appearance/theme-provider";
import { useDensity, type Density } from "@/features/appearance/density-provider";

const THEMES: { id: ThemePreference; label: string; blurb: string }[] = [
  { id: "light", label: "Light", blurb: "Bright surfaces." },
  { id: "dark", label: "Dark", blurb: "Dark surfaces, same layout." },
  { id: "system", label: "System", blurb: "Follow your device." },
];

const DENSITIES: { id: Density; label: string; blurb: string }[] = [
  { id: "comfortable", label: "Comfortable", blurb: "Roomy rows for reading." },
  { id: "compact", label: "Compact", blurb: "Tighter rows, more on screen." },
];

type Option = { id: string; label: string; blurb: string };

function OptionList({
  options,
  current,
  onSelect,
}: {
  options: Option[];
  current: string;
  onSelect: (id: string) => void;
}) {
  return (
    <ul className="grid gap-2 sm:grid-cols-3">
      {options.map((option) => {
        const active = current === option.id;
        return (
          <li key={option.id}>
            <button
              type="button"
              aria-pressed={active}
              onClick={() => onSelect(option.id)}
              className={`min-h-11 w-full rounded-[var(--radius)] border px-3 py-3 text-left transition ${
                active
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--border)] hover:bg-[var(--canvas)]"
              }`}
            >
              <p className="text-sm font-medium text-[var(--ink)]">
                {option.label}
                {active ? " · current" : ""}
              </p>
              <p className="mt-1 text-xs text-[var(--muted)]">{option.blurb}</p>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export function AppearanceSection() {
  const { preference, setPreference } = useTheme();
  const { density, setDensity } = useDensity();

  return (
    <div className="flex flex-col gap-4">
      <Card id="settings-theme-heading" title="Theme">
        <OptionList
          options={THEMES}
          current={preference}
          onSelect={(id) => setPreference(id as ThemePreference)}
        />
      </Card>
      <Card id="settings-density-heading" title="Density">
        <OptionList
          options={DENSITIES}
          current={density}
          onSelect={(id) => setDensity(id as Density)}
        />
      </Card>
    </div>
  );
}
