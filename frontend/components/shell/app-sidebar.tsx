"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Brain,
  Cable,
  CalendarDays,
  CircleHelp,
  Inbox,
  ListChecks,
  Mail,
  MessageSquare,
  Settings,
  Sun,
  Target,
  Timer,
} from "lucide-react";
import { isNavActive, NAV_GROUPS, type NavHref } from "./nav";

const ICONS: Record<NavHref, ComponentType<{ className?: string; "aria-hidden"?: boolean }>> = {
  "/": Sun,
  "/chat": MessageSquare,
  "/inbox": Inbox,
  "/tasks": ListChecks,
  "/goals": Target,
  "/calendar": CalendarDays,
  "/mail": Mail,
  "/memory": Brain,
  "/routines": Timer,
  "/activity": Activity,
  "/connections": Cable,
  "/settings": Settings,
  "/help": CircleHelp,
};

export type AppSidebarProps = {
  open: boolean;
  onNavigate: () => void;
  /** Count of items waiting on the owner; drives the Inbox badge. Hidden when 0 or unknown. */
  needsYouCount?: number | null;
};

export function AppSidebar({ open, onNavigate, needsYouCount }: AppSidebarProps) {
  const pathname = usePathname();
  const needsYou = needsYouCount && needsYouCount > 0 ? needsYouCount : 0;

  return (
    <aside
      id="app-sidebar"
      className={`fixed top-0 left-0 z-40 flex h-dvh w-[16.5rem] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] transition-transform duration-200 motion-reduce:transition-none ${
        open ? "translate-x-0" : "-translate-x-full max-md:invisible"
      } md:visible md:sticky md:translate-x-0`}
    >
      <div className="border-b border-[var(--border)] px-5 py-5">
        <Link href="/" onClick={onNavigate} className="block">
          <p className="text-[0.7rem] font-medium tracking-[0.22em] text-[var(--muted)] uppercase">
            Personal agent
          </p>
          <p
            className="mt-1 text-4xl leading-none font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            AURA
          </p>
        </Link>
      </div>

      <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-3 py-4" aria-label="Primary">
        {NAV_GROUPS.map((group) => {
          const label = "label" in group ? group.label : undefined;
          const isFooter = group.id === "footer";
          return (
            <div
              key={group.id}
              role="group"
              aria-label={label}
              className={`flex flex-col gap-1 ${isFooter ? "mt-auto border-t border-[var(--border)] pt-4" : ""}`}
            >
              {label ? (
                <p className="px-3 pb-1 text-[0.7rem] font-medium tracking-[0.16em] text-[var(--muted)] uppercase">
                  {label}
                </p>
              ) : null}
              {group.items.map((item) => {
                const active = isNavActive(pathname, item.href);
                const Icon = ICONS[item.href];
                const showBadge =
                  "badgeKey" in item && item.badgeKey === "needsYou" && needsYou > 0;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    onClick={onNavigate}
                    className={`relative flex items-center gap-3 rounded-[var(--radius)] px-3 py-2.5 text-sm font-medium transition-colors duration-200 motion-reduce:transition-none ${
                      active
                        ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "text-[var(--ink)] hover:bg-[var(--canvas)]"
                    }`}
                  >
                    <span
                      aria-hidden
                      className={`absolute top-1/2 left-0 h-5 w-1 -translate-y-1/2 rounded-full bg-[var(--accent)] transition-transform duration-200 motion-reduce:transition-none ${
                        active ? "scale-y-100" : "scale-y-0"
                      }`}
                    />
                    <Icon className="h-4 w-4 shrink-0" aria-hidden />
                    <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    {showBadge ? (
                      <span
                        className="inline-flex min-w-5 items-center justify-center rounded-full bg-[var(--accent)] px-1.5 text-xs font-semibold text-white"
                        aria-label={`${needsYou} waiting on you`}
                      >
                        {needsYou > 9 ? "9+" : needsYou}
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
