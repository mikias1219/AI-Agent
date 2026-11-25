"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export type HubTab = { id: string; label: string; href: string };

export type HubChromeProps = {
  /** Accessible name for the tablist (destination name). */
  label: string;
  tabs: HubTab[];
};

/**
 * One tab row for a destination hub. The shell header already shows the destination
 * title, so this component does not repeat it.
 */
export function HubChrome({ label, tabs }: HubChromeProps) {
  const pathname = usePathname();
  const router = useRouter();
  const active =
    tabs.find((tab) => pathname === tab.href || pathname.startsWith(`${tab.href}/`))?.id ??
    tabs[0]?.id;

  return (
    <div>
      <div
        role="tablist"
        aria-label={label}
        className="flex w-fit max-w-full gap-1 overflow-x-auto rounded-[var(--radius)] border border-[var(--border)] bg-[var(--subtle)] p-1"
      >
        {tabs.map((tab) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={selected}
              tabIndex={selected ? 0 : -1}
              className={`min-h-11 shrink-0 rounded-[var(--radius-sm)] px-3 py-1.5 text-[length:var(--text-body)] font-medium transition-[background-color,color,box-shadow] duration-150 motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none md:min-h-0 ${
                selected
                  ? "bg-[var(--surface)] text-[var(--accent-strong)] shadow-[var(--shadow-1)] ring-1 ring-[var(--border)]"
                  : "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--ink)]"
              }`}
              onClick={() => {
                if (!selected) router.push(tab.href);
              }}
              onKeyDown={(event) => {
                const index = tabs.findIndex((row) => row.id === tab.id);
                if (event.key === "ArrowRight") {
                  event.preventDefault();
                  const next = tabs[(index + 1) % tabs.length];
                  if (next) router.push(next.href);
                } else if (event.key === "ArrowLeft") {
                  event.preventDefault();
                  const next = tabs[(index - 1 + tabs.length) % tabs.length];
                  if (next) router.push(next.href);
                }
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <nav className="sr-only" aria-label={`${label} links`}>
        {tabs.map((tab) => (
          <Link key={tab.href} href={tab.href}>
            {tab.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
