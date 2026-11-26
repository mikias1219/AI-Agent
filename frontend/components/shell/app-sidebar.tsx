"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  GraduationCap,
  Inbox,
  Library,
  ListChecks,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Settings,
  Sparkles,
  Sun,
  Wallet,
} from "lucide-react";
import { Avatar } from "@/components/ui/avatar";
import { isNavActive, NAV_GROUPS, type NavBadgeKey, type NavCounts, type NavHref } from "./nav";

const ICONS: Record<NavHref, ComponentType<{ className?: string; "aria-hidden"?: boolean }>> = {
  "/": Sun,
  "/library": Library,
  "/learn": GraduationCap,
  "/inbox": Inbox,
  "/tasks": ListChecks,
  "/money": Wallet,
  "/agent": Bot,
  "/settings": Settings,
};

/** What each count means, for screen readers and tooltips. */
const BADGE_LABEL: Record<NavBadgeKey, (n: number) => string> = {
  needsYou: (n) => `${n} waiting on you`,
  tasksLeft: (n) => `${n} tasks left today`,
  wordsDue: (n) => `${n} words due`,
};

export type AppSidebarProps = {
  open: boolean;
  onNavigate: () => void;
  /** Icon-only rail on desktop. The mobile drawer is always expanded. */
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  /** Opens the one add sheet (expense, income, task, note, mood). */
  onQuickAdd?: () => void;
  /** Counts shown beside Plan, Needs you and Learn; hidden when zero or unknown. */
  counts?: NavCounts;
  /** Kept for callers that only know the approvals count. */
  needsYouCount?: number | null;
  agentPaused?: boolean | null;
  /** Owner's name and photo for the profile row; initials show when there is no photo. */
  ownerName?: string;
  photoSrc?: string;
};

function badgeText(n: number): string {
  return n > 99 ? "99+" : String(n);
}

/**
 * Sidebar (redesign): logo, one Add button, Daily and Grow groups with counts, Agent and
 * Settings at the bottom, then one profile row that carries the agent status and Collapse.
 */
export function AppSidebar({
  open,
  onNavigate,
  collapsed = false,
  onToggleCollapsed,
  onQuickAdd,
  counts,
  needsYouCount,
  agentPaused = null,
  ownerName = "",
  photoSrc,
}: AppSidebarProps) {
  const pathname = usePathname();
  const allCounts: NavCounts = { needsYou: needsYouCount ?? null, ...counts };

  return (
    <aside
      id="app-sidebar"
      data-collapsed={collapsed || undefined}
      className={`group/side fixed top-0 left-0 z-40 flex h-dvh w-[var(--nav-width)] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] transition-[transform,width,box-shadow] duration-200 ease-out motion-reduce:transition-none ${
        open ? "translate-x-0 shadow-[var(--shadow-3)]" : "-translate-x-full max-md:invisible"
      } md:visible md:sticky md:translate-x-0 md:shadow-none ${collapsed ? "md:w-[4.5rem]" : ""}`}
    >
      <div
        className={`flex h-[var(--header-height)] shrink-0 items-center gap-2.5 px-5 ${collapsed ? "md:justify-center md:gap-0 md:px-0" : ""}`}
      >
        <span
          aria-hidden
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--accent)] text-[var(--on-accent)] shadow-[var(--shadow-1)]"
        >
          <Sparkles className="h-[18px] w-[18px]" strokeWidth={2} />
        </span>
        <span
          className={`text-[length:var(--text-title)] font-semibold tracking-[0.14em] text-[var(--ink)] ${collapsed ? "md:hidden" : ""}`}
        >
          Compass
        </span>
      </div>

      {onQuickAdd ? (
        <div className={`px-3 pb-4 ${collapsed ? "md:px-2" : ""}`}>
          <button
            type="button"
            onClick={() => {
              onNavigate();
              onQuickAdd();
            }}
            aria-label="Add expense, income, task, note or mood"
            data-tip="Add"
            className={`compass-tip inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-[var(--radius)] bg-[var(--accent)] px-3 text-[length:var(--text-body)] font-semibold text-[var(--on-accent)] shadow-[var(--shadow-1)] transition-[filter,transform] duration-150 hover:brightness-105 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:scale-[0.98] motion-reduce:transition-none ${collapsed ? "md:px-0" : ""}`}
          >
            <Plus className="h-5 w-5 shrink-0" aria-hidden />
            <span className={collapsed ? "md:sr-only" : ""}>Add</span>
          </button>
        </div>
      ) : null}

      <nav
        className={`flex flex-1 flex-col gap-5 overflow-x-hidden overflow-y-auto px-3 pb-3 ${collapsed ? "md:overflow-visible" : ""}`}
        aria-label="Primary"
      >
        {NAV_GROUPS.map((group) => {
          const isFooter = group.id === "footer";
          return (
            <div
              key={group.id}
              role="group"
              aria-label={group.label || "More"}
              className={`flex flex-col gap-0.5 ${isFooter ? "mt-auto" : ""}`}
            >
              {group.label ? (
                <p
                  aria-hidden
                  className={`px-3 pb-1 text-[11px] font-semibold tracking-[0.08em] text-[var(--muted)] uppercase ${collapsed ? "md:hidden" : ""}`}
                >
                  {group.label}
                </p>
              ) : null}
              {collapsed && isFooter ? (
                <span aria-hidden className="mx-2 mb-1 hidden h-px bg-[var(--border)] md:block" />
              ) : null}
              {group.items.map((item) => {
                const active = isNavActive(pathname, item.href);
                const Icon = ICONS[item.href];
                const key = "badgeKey" in item ? (item.badgeKey as NavBadgeKey) : null;
                const count = key ? (allCounts[key] ?? 0) : 0;
                const showBadge = key !== null && count > 0;
                const urgent = key === "needsYou";
                const hint = "hint" in item ? item.hint : undefined;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? undefined : hint}
                    data-tip={item.label}
                    onClick={onNavigate}
                    className={`compass-tip relative flex min-h-[40px] items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-[length:var(--text-body)] transition-colors duration-150 motion-reduce:transition-none ${
                      collapsed ? "md:justify-center md:gap-0 md:px-0" : ""
                    } ${
                      active
                        ? "bg-[var(--accent-soft)] font-semibold text-[var(--accent-strong)]"
                        : `font-medium hover:bg-[var(--hover)] active:bg-[var(--pressed)] ${isFooter ? "text-[var(--muted)] hover:text-[var(--ink)]" : "text-[var(--ink)]"}`
                    }`}
                  >
                    <Icon
                      className={`h-[18px] w-[18px] shrink-0 ${active ? "" : "text-[var(--muted)]"}`}
                      aria-hidden
                    />
                    <span
                      className={`min-w-0 flex-1 truncate ${collapsed ? "md:sr-only md:flex-none" : ""}`}
                    >
                      {item.label}
                    </span>
                    {showBadge && key ? (
                      <span
                        className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[11px] leading-none font-semibold tabular-nums ${
                          urgent
                            ? "bg-[var(--warning)] text-[var(--on-status)]"
                            : "bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                        } ${collapsed ? "md:absolute md:top-1 md:right-2 md:h-4 md:min-w-4 md:px-1 md:text-[10px] md:ring-2 md:ring-[var(--surface)]" : ""}`}
                        aria-label={BADGE_LABEL[key](count)}
                      >
                        {badgeText(count)}
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>

      <div
        className={`flex items-center gap-2 border-t border-[var(--border)] px-3 py-3 ${collapsed ? "md:flex-col md:px-2" : ""}`}
      >
        <Link
          href="/settings"
          onClick={onNavigate}
          title="Your profile"
          className={`flex min-h-[44px] min-w-0 flex-1 items-center gap-3 rounded-[var(--radius)] px-2 py-1.5 transition-colors duration-150 hover:bg-[var(--hover)] motion-reduce:transition-none ${collapsed ? "md:justify-center md:px-0" : ""}`}
        >
          <Avatar name={ownerName} src={photoSrc} size="sm" />
          <span className={`min-w-0 flex-1 ${collapsed ? "md:sr-only" : ""}`}>
            <span className="block truncate text-[length:var(--text-body)] leading-5 font-semibold text-[var(--ink)]">
              {ownerName || "Your profile"}
            </span>
            <span
              role="status"
              className={`flex items-center gap-1.5 text-[length:var(--text-caption)] leading-4 ${
                agentPaused ? "text-[var(--warning)]" : "text-[var(--muted)]"
              }`}
            >
              <span
                aria-hidden
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                  agentPaused === null
                    ? "bg-[var(--border-strong,var(--border))]"
                    : agentPaused
                      ? "bg-[var(--warning)]"
                      : "bg-[var(--success)]"
                }`}
              />
              {agentPaused === null
                ? "Agent status unknown"
                : agentPaused
                  ? "Agent paused"
                  : "Agent on"}
            </span>
          </span>
        </Link>
        {onToggleCollapsed ? (
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-pressed={collapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            data-tip={collapsed ? "Expand" : "Collapse"}
            className="compass-tip hidden h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius)] text-[var(--muted)] transition-colors duration-150 hover:bg-[var(--hover)] hover:text-[var(--ink)] md:inline-flex motion-reduce:transition-none"
          >
            {collapsed ? (
              <PanelLeftOpen className="h-[18px] w-[18px]" aria-hidden />
            ) : (
              <PanelLeftClose className="h-[18px] w-[18px]" aria-hidden />
            )}
          </button>
        ) : null}
      </div>
    </aside>
  );
}
