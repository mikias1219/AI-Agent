"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export type HubTab = { id: string; label: string; href: string };

export type HubChromeProps = {
  eyebrow: string;
  title: string;
  description: string;
  tabs: HubTab[];
};

/** Shared page intro + related-feature tabs for Work / Schedule / Agent hubs. */
export function HubChrome({ eyebrow, title, description, tabs }: HubChromeProps) {
  const pathname = usePathname();
  const router = useRouter();
  const active =
    tabs.find((tab) => pathname === tab.href || pathname.startsWith(`${tab.href}/`))?.id ??
    tabs[0]?.id;

  return (
    <header className="flex flex-col gap-4">
      <div>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">{eyebrow}</p>
        <h1
          className="mt-1 text-[26px] leading-[32px] font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {title}
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">{description}</p>
      </div>
      <div
        role="tablist"
        aria-label={`${eyebrow} sections`}
        className="flex w-fit flex-wrap gap-1 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-1"
      >
        {tabs.map((tab) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={selected}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                selected
                  ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "text-[var(--muted)] hover:bg-[var(--canvas)] hover:text-[var(--ink)]"
              }`}
              onClick={() => {
                if (!selected) router.push(tab.href);
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      {/* Keep crawlable links for a11y / no-JS fallbacks */}
      <nav className="sr-only" aria-label={`${eyebrow} links`}>
        {tabs.map((tab) => (
          <Link key={tab.href} href={tab.href}>
            {tab.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
