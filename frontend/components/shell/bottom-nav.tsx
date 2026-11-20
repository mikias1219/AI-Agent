"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Inbox, ListChecks, Menu, MessageSquare, Sun } from "lucide-react";
import { BOTTOM_NAV, isNavActive } from "./nav";

const ICONS: Record<string, ComponentType<{ className?: string; "aria-hidden"?: boolean }>> = {
  "/": Sun,
  "/chat": MessageSquare,
  "/inbox": Inbox,
  "/tasks": ListChecks,
};

export type BottomNavProps = {
  needsYouCount?: number | null;
  onOpenMore: () => void;
};

/** Phone navigation. Desktop keeps the sidebar. */
export function BottomNav({ needsYouCount = null, onOpenMore }: BottomNavProps) {
  const pathname = usePathname();
  const needsYou = needsYouCount && needsYouCount > 0 ? needsYouCount : 0;

  return (
    <nav
      aria-label="Mobile"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-[var(--border)] bg-[var(--surface)] md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <ul className="grid grid-cols-5" style={{ minHeight: "var(--bottom-nav-height)" }}>
        {BOTTOM_NAV.map((item) => {
          const active = isNavActive(pathname, item.href);
          const Icon = ICONS[item.href] ?? Sun;
          const showBadge = "badgeKey" in item && item.badgeKey === "needsYou" && needsYou > 0;
          return (
            <li key={item.href} className="min-w-0">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex h-full min-h-[44px] flex-col items-center justify-center gap-0.5 px-1 text-[length:var(--text-caption)] font-medium ${
                  active ? "text-[var(--accent)]" : "text-[var(--muted)]"
                }`}
              >
                <span className="relative">
                  <Icon className="h-5 w-5" aria-hidden />
                  {showBadge ? (
                    <span className="absolute -top-1 -right-2 inline-flex min-w-4 items-center justify-center rounded-full bg-[var(--warning)] px-1 text-[10px] font-semibold text-white">
                      {needsYou > 9 ? "9+" : needsYou}
                    </span>
                  ) : null}
                </span>
                <span className="truncate">{item.label}</span>
              </Link>
            </li>
          );
        })}
        <li className="min-w-0">
          <button
            type="button"
            onClick={onOpenMore}
            className="flex h-full min-h-[44px] w-full flex-col items-center justify-center gap-0.5 px-1 text-[length:var(--text-caption)] font-medium text-[var(--muted)]"
          >
            <Menu className="h-5 w-5" aria-hidden />
            More
          </button>
        </li>
      </ul>
    </nav>
  );
}
