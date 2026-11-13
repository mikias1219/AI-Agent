"use client";

import { useTheme, type ThemePreference } from "@/features/appearance/theme-provider";
import { useDensity, type Density } from "@/features/appearance/density-provider";

const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

const THEMES: { id: ThemePreference; label: string; blurb: string }[] = [
  { id: "light", label: "Light", blurb: "Canvas and surfaces from the mockup light palette." },
  { id: "dark", label: "Dark", blurb: "Same layout and color roles on dark surfaces." },
  { id: "system", label: "System", blurb: "Follow the OS light/dark preference." },
];

const DENSITIES: { id: Density; label: string; blurb: string }[] = [
  { id: "comfortable", label: "Comfortable", blurb: "Default spacing for reading." },
  { id: "compact", label: "Compact", blurb: "Tighter rows (36px) as in the mockup compact Today." },
];

export function AppearanceSection() {
  const { preference, setPreference } = useTheme();
  const { density, setDensity } = useDensity();

  return (
    <div className="flex flex-col gap-4">
      <section className={panelClass} aria-labelledby="settings-theme-heading">
        <h2 id="settings-theme-heading" className="text-sm font-semibold text-[var(--ink)]">
          Theme
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Color means something. Accent is for actions; success/warning/danger are for status only.
        </p>
        <ul className="mt-4 flex flex-col gap-2">
          {THEMES.map((option) => {
            const active = preference === option.id;
            return (
              <li key={option.id}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => setPreference(option.id)}
                  className={`w-full rounded-[var(--radius)] border px-3 py-3 text-left transition ${
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
      </section>

      <section className={panelClass} aria-labelledby="settings-density-heading">
        <h2 id="settings-density-heading" className="text-sm font-semibold text-[var(--ink)]">
          Density
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Applies across list rows and Today cards. You can also toggle on Today.
        </p>
        <ul className="mt-4 flex flex-col gap-2">
          {DENSITIES.map((option) => {
            const active = density === option.id;
            return (
              <li key={option.id}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => setDensity(option.id)}
                  className={`w-full rounded-[var(--radius)] border px-3 py-3 text-left transition ${
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
      </section>
    </div>
  );
}
