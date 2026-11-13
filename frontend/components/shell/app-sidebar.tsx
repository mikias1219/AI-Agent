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
  /** From agent control; null when unknown. */
  agentPaused?: boolean | null;
};

export function AppSidebar({
  open,
  onNavigate,
  needsYouCount,
  agentPaused = null,
}: AppSidebarProps) {
  const pathname = usePathname();
  const needsYou = needsYouCount && needsYouCount > 0 ? needsYouCount : 0;

  return (
    <aside
      id="app-sidebar"
      className={`fixed top-0 left-0 z-40 flex h-dvh w-[var(--nav-width)] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] transition-transform duration-200 motion-reduce:transition-none ${
        open ? "translate-x-0" : "-translate-x-full max-md:invisible"
      } md:visible md:sticky md:translate-x-0`}
    >
      <div className="border-b border-[var(--border)] px-3 py-5">
        <Link href="/" onClick={onNavigate} className="block px-3">
          <p className="text-xl font-semibold tracking-tight text-[var(--ink)]">AURA</p>
        </Link>
      </div>

      <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-3 py-4" aria-label="Primary">
        {NAV_GROUPS.map((group) => {
          const label = "label" in group ? group.label : undefined;
          const isFooter = group.id === "footer";
          const isAura = group.id === "aura";
          return (
            <div
              key={group.id}
              role="group"
              aria-label={label}
              className={`flex flex-col gap-0.5 ${isFooter ? "mt-auto border-t border-[var(--border)] pt-3" : ""}`}
            >
              {label ? <p className="px-3 pb-1 text-xs text-[var(--muted)]">{label}</p> : null}
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
                    className={`relative flex items-center gap-3 rounded-lg px-3 py-[7px] text-sm font-medium transition-colors duration-200 motion-reduce:transition-none ${
                      active
                        ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "text-[var(--ink)] hover:bg-[var(--canvas)]"
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden />
                    <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    {showBadge ? (
                      <span
                        className="inline-flex min-w-5 items-center justify-center rounded-full bg-[var(--warning)] px-1.5 text-xs font-semibold text-white"
                        aria-label={`${needsYou} waiting on you`}
                      >
                        {needsYou > 9 ? "9+" : needsYou}
                      </span>
                    ) : null}
                  </Link>
                );
              })}
              {isAura && agentPaused !== null ? (
                <p
                  className={`px-3 pt-2 text-xs ${agentPaused ? "text-[var(--warning)]" : "text-[var(--success)]"}`}
                  role="status"
                >
                  {agentPaused ? "Agent paused" : "Agent listening"}
                </p>
              ) : null}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
