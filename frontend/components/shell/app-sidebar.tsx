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
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Sparkles,
  Sun,
} from "lucide-react";
import { Avatar } from "@/components/ui/avatar";
import { isNavActive, NAV_GROUPS, type NavHref } from "./nav";

const ICONS: Record<NavHref, ComponentType<{ className?: string; "aria-hidden"?: boolean }>> = {
  "/": Sun,
  "/chat": MessageSquare,
  "/library": Library,
  "/learn": GraduationCap,
  "/inbox": Inbox,
  "/tasks": ListChecks,
  "/agent": Bot,
  "/settings": Settings,
};

export type AppSidebarProps = {
  open: boolean;
  onNavigate: () => void;
  /** Icon-only rail on desktop. The mobile drawer is always expanded. */
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  needsYouCount?: number | null;
  agentPaused?: boolean | null;
  /** Owner's name and photo for the header; initials show when there is no photo. */
  ownerName?: string;
  photoSrc?: string;
};

export function AppSidebar({
  open,
  onNavigate,
  collapsed = false,
  onToggleCollapsed,
  needsYouCount,
  agentPaused = null,
  ownerName = "",
  photoSrc,
}: AppSidebarProps) {
  const pathname = usePathname();
  const needsYou = needsYouCount && needsYouCount > 0 ? needsYouCount : 0;

  const GROUP_LABEL: Record<string, string> = { primary: "Your life", footer: "Manage" };

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
          className={`text-[length:var(--text-title)] font-semibold tracking-[0.14em] text-[var(--ink)] transition-opacity duration-150 ${collapsed ? "md:hidden" : ""}`}
        >
          AURA
        </span>
      </div>

      <div className="px-3 pb-3">
        <Link
          href="/settings"
          onClick={onNavigate}
          title="Your profile"
          className={`flex min-h-[52px] items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[color-mix(in_srgb,var(--subtle)_55%,var(--surface))] px-2.5 py-2 transition-colors duration-150 hover:bg-[var(--subtle)] motion-reduce:transition-none ${collapsed ? "md:justify-center md:gap-0 md:border-transparent md:bg-transparent md:px-0" : ""}`}
        >
          <Avatar name={ownerName} src={photoSrc} size="sm" />
          <span className={`min-w-0 flex-1 ${collapsed ? "md:sr-only" : ""}`}>
            <span className="block truncate text-[length:var(--text-body)] leading-5 font-semibold text-[var(--ink)]">
              {ownerName || "Your profile"}
            </span>
            {agentPaused !== null ? (
              <span
                role="status"
                className={`flex items-center gap-1.5 text-[length:var(--text-caption)] leading-4 font-medium ${
                  agentPaused ? "text-[var(--warning)]" : "text-[var(--muted)]"
                }`}
              >
                <span
                  aria-hidden
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${agentPaused ? "bg-[var(--warning)]" : "bg-[var(--success)]"}`}
                />
                {agentPaused ? "AURA is paused" : "AURA is listening"}
              </span>
            ) : (
              <span className="block truncate text-[length:var(--text-caption)] leading-4 text-[var(--muted)]">
                Your personal space
              </span>
            )}
          </span>
        </Link>
      </div>

      <nav
        className={`flex flex-1 flex-col gap-4 overflow-y-auto px-3 pb-3 ${collapsed ? "md:overflow-visible" : ""}`}
        aria-label="Primary"
      >
        {NAV_GROUPS.map((group) => {
          const isFooter = group.id === "footer";
          return (
            <div
              key={group.id}
              role="group"
              aria-label={group.id}
              className={`flex flex-col gap-0.5 ${isFooter ? "mt-auto" : ""}`}
            >
              <p
                aria-hidden
                className={`px-3 pb-1 text-[length:var(--text-caption)] font-semibold tracking-[0.08em] text-[var(--muted)] uppercase ${collapsed ? "md:hidden" : ""}`}
              >
                {GROUP_LABEL[group.id]}
              </p>
              {collapsed && isFooter ? (
                <span aria-hidden className="mx-2 mb-1 hidden h-px bg-[var(--border)] md:block" />
              ) : null}
              {group.items.map((item) => {
                const active = isNavActive(pathname, item.href);
                const Icon = ICONS[item.href];
                const showBadge =
                  "badgeKey" in item && item.badgeKey === "needsYou" && needsYou > 0;
                const hint = "hint" in item ? item.hint : undefined;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? undefined : hint}
                    data-tip={item.label}
                    onClick={onNavigate}
                    className={`aura-tip relative flex min-h-[44px] items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-[length:var(--text-body)] font-medium transition-colors duration-150 before:absolute before:top-1/2 before:left-0 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-[var(--accent)] before:transition-opacity before:duration-150 motion-reduce:transition-none ${
                      collapsed ? "md:justify-center md:gap-0 md:px-0" : ""
                    } ${
                      active
                        ? "bg-[var(--accent-soft)] text-[var(--accent-strong)] before:opacity-100"
                        : "text-[var(--ink)] before:opacity-0 hover:bg-[var(--hover)] active:bg-[var(--pressed)]"
                    }`}
                  >
                    <Icon
                      className={`h-5 w-5 shrink-0 ${active ? "" : "text-[var(--muted)]"}`}
                      aria-hidden
                    />
                    <span
                      className={`min-w-0 flex-1 truncate ${collapsed ? "md:sr-only md:flex-none" : ""}`}
                    >
                      {item.label}
                    </span>
                    {showBadge ? (
                      <span
                        className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[var(--warning)] px-1.5 text-[length:var(--text-caption)] leading-none font-semibold text-[var(--on-status)] ${collapsed ? "md:absolute md:top-1 md:right-2 md:h-4 md:min-w-4 md:px-1 md:text-[10px] md:ring-2 md:ring-[var(--surface)]" : ""}`}
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
      {onToggleCollapsed ? (
        <div className="hidden px-3 pt-1 pb-3 md:block">
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-pressed={collapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            data-tip={collapsed ? "Expand" : "Collapse"}
            className={`aura-tip flex min-h-[40px] w-full items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-[length:var(--text-small)] text-[var(--muted)] transition-colors duration-150 hover:bg-[var(--hover)] hover:text-[var(--ink)] motion-reduce:transition-none ${collapsed ? "justify-center gap-0 px-0" : ""}`}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-5 w-5 shrink-0" aria-hidden />
            ) : (
              <PanelLeftClose className="h-5 w-5 shrink-0" aria-hidden />
            )}
            <span className={collapsed ? "sr-only" : ""}>Collapse</span>
          </button>
        </div>
      ) : null}
    </aside>
  );
}
