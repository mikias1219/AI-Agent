const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

const TOKENS: { name: string; role: string; var: string }[] = [
  { name: "Canvas", role: "App background", var: "--canvas" },
  { name: "Surface", role: "Cards and panels", var: "--surface" },
  { name: "Ink", role: "Primary text", var: "--ink" },
  { name: "Muted", role: "Secondary text", var: "--muted" },
  { name: "Accent", role: "Links and active nav", var: "--accent" },
  { name: "Accent soft", role: "Selected backgrounds", var: "--accent-soft" },
  { name: "Border", role: "Dividers", var: "--border" },
  { name: "Danger", role: "Errors", var: "--danger" },
  { name: "Warning", role: "Caution states", var: "--warning" },
  { name: "Success", role: "Healthy states", var: "--success" },
  { name: "Radius", role: "Corner radius (12px)", var: "--radius" },
];

export function AppearanceSection() {
  return (
    <section className={panelClass} aria-labelledby="settings-appearance-heading">
      <h2 id="settings-appearance-heading" className="text-sm font-semibold text-[var(--ink)]">
        Design tokens
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        AURA uses a light professional palette defined in{" "}
        <code className="rounded bg-[var(--canvas)] px-1 py-0.5 text-xs">styles/tokens.css</code>.
        Theme switching and per-user persistence are not implemented; these values apply globally.
      </p>
      <ul className="mt-4 flex flex-col gap-2">
        {TOKENS.map((token) => (
          <li
            key={token.var}
            className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--canvas)] px-3 py-2"
          >
            <span
              className="h-8 w-8 shrink-0 rounded-md border border-[var(--border)]"
              style={{
                background: token.var === "--radius" ? "var(--surface)" : `var(${token.var})`,
                boxShadow: token.var === "--radius" ? "inset 0 0 0 3px var(--accent)" : undefined,
              }}
              aria-hidden
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-[var(--ink)]">{token.name}</p>
              <p className="text-xs text-[var(--muted)]">{token.role}</p>
            </div>
            <code className="text-xs text-[var(--muted)]">{token.var}</code>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-[var(--muted)]">
        Typography: display headings use the serif display font from the root layout; UI copy uses
        the sans stack. Motion uses short fades and slides; reduced-motion prefers no animation.
      </p>
    </section>
  );
}
