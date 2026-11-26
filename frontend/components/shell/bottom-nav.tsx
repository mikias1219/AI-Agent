"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Inbox, ListChecks, Plus, Sun, Wallet } from "lucide-react";
import { BOTTOM_NAV, isNavActive } from "./nav";

type IconType = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;

const ICONS: Record<string, IconType> = {
  "/": Sun,
  "/tasks": ListChecks,
  "/money": Wallet,
  "/inbox": Inbox,
};

export type BottomNavProps = {
  /** Opens the one add sheet (expense, income, task, note, mood). */
  onQuickAdd: () => void;
};

/**
 * Phone navigation: Today, Plan, a central +, Money, Needs you. Everything else (Learn,
 * Library, Agent, Settings) is in the menu button in the header.
 */
export function BottomNav({ onQuickAdd }: BottomNavProps) {
  const pathname = usePathname();
  const left = BOTTOM_NAV.slice(0, 2);
  const right = BOTTOM_NAV.slice(2);

  const link = (item: (typeof BOTTOM_NAV)[number]) => {
    const active = isNavActive(pathname, item.href);
    const Icon = ICONS[item.href] ?? Sun;
    return (
      <li key={item.href} className="min-w-0">
        <Link
          href={item.href}
          aria-current={active ? "page" : undefined}
          className={`relative flex h-full min-h-[48px] flex-col items-center justify-center gap-0.5 px-1 text-[length:var(--text-caption)] leading-4 font-medium transition-colors duration-150 active:bg-[var(--pressed)] ${
            active ? "text-[var(--accent-strong)]" : "text-[var(--muted)]"
          }`}
        >
          <span
            aria-hidden
            className={`absolute top-0 h-[3px] w-8 rounded-b-full bg-[var(--accent)] transition-opacity duration-150 ${active ? "opacity-100" : "opacity-0"}`}
          />
          <Icon className="h-5 w-5" aria-hidden />
          <span className="truncate">{item.label}</span>
        </Link>
      </li>
    );
  };

  return (
    <nav
      aria-label="Mobile"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-[var(--border)] bg-[color-mix(in_srgb,var(--surface)_92%,transparent)] backdrop-blur-md md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <ul className="grid grid-cols-5" style={{ minHeight: "var(--bottom-nav-height)" }}>
        {left.map(link)}
        <li className="flex min-w-0 items-center justify-center">
          <button
            type="button"
            onClick={onQuickAdd}
            aria-label="Add expense, income, task, note or mood"
            className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--on-accent,#fff)] shadow-[var(--shadow-2)] active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <Plus className="h-6 w-6" aria-hidden />
          </button>
        </li>
        {right.map(link)}
      </ul>
    </nav>
  );
}
