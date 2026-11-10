"use client";

import { displayName } from "@/lib/auth/session";
import { useAuth } from "@/features/auth/use-auth";

const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

export function AccountSection() {
  const { status } = useAuth();
  const user = status?.user ?? null;
  const name = displayName(user);

  return (
    <section className={panelClass} aria-labelledby="settings-account-heading">
      <h2 id="settings-account-heading" className="text-sm font-semibold text-[var(--ink)]">
        Profile
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Workspace owner from the auth API. Password and registration changes are not in this UI
        yet.
      </p>
      <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Name</dt>
          <dd className="mt-1 font-medium text-[var(--ink)]">{name}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Email</dt>
          <dd className="mt-1 font-medium text-[var(--ink)]">{user?.email || "Not on file"}</dd>
        </div>
      </dl>
    </section>
  );
}
