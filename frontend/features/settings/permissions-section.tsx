const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

const BULLETS = [
  "Sessions are HTTP-only cookies issued by the Python backend after login or registration.",
  "This browser only calls same-origin /api (proxied to the backend in dev). It does not store API keys.",
  "Chat, tasks, activity, and Telegram screens use live APIs when the backend is up. Google uses live APIs when connected.",
  "Tool calls that change production data may require explicit approval on the Tasks page before the agent continues.",
  "Telegram bot tokens, Google OAuth secrets, and model configuration belong in backend environment files — not in the frontend.",
  "There is no multi-user sharing, delegated access, or fine-grained OAuth consent UI in this release.",
  "Account deletion, data export, and worker privacy controls are planned; nothing here pretends they exist.",
];

export function PermissionsSection() {
  return (
    <section className={panelClass} aria-labelledby="settings-permissions-heading">
      <h2 id="settings-permissions-heading" className="text-sm font-semibold text-[var(--ink)]">
        Access & honesty
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        What this dashboard can and cannot do today. No invented toggles.
      </p>
      <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-[var(--ink)]">
        {BULLETS.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
