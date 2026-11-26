"use client";

import { useEffect, useRef, type ComponentType } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  GraduationCap,
  Inbox,
  Library,
  ListChecks,
  Menu,
  MessageSquare,
  Settings,
  Sun,
  Wallet,
} from "lucide-react";
import { focusFirst, trapFocus } from "@/lib/focus-trap";
import { BOTTOM_NAV, MORE_NAV, isNavActive } from "./nav";

type IconType = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;

const ICONS: Record<string, IconType> = {
  "/": Sun,
  "/chat": MessageSquare,
  "/library": Library,
  "/learn": GraduationCap,
  "/tasks": ListChecks,
  "/money": Wallet,
  "/inbox": Inbox,
  "/agent": Bot,
  "/settings": Settings,
};

export type BottomNavProps = {
  needsYouCount?: number | null;
  moreOpen: boolean;
  onOpenMore: () => void;
  onCloseMore: () => void;
};

/** Phone navigation: four destinations and a More sheet. Desktop keeps the sidebar. */
export function BottomNav({
  needsYouCount = null,
  moreOpen,
  onOpenMore,
  onCloseMore,
}: BottomNavProps) {
  const pathname = usePathname();
  const needsYou = needsYouCount && needsYouCount > 0 ? needsYouCount : 0;
  const moreActive = MORE_NAV.some((item) => isNavActive(pathname, item.href));
  const sheetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!moreOpen) return;
    const panel = sheetRef.current;
    if (panel) focusFirst(panel);
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onCloseMore();
      if (panel) trapFocus(panel, event);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [moreOpen, onCloseMore]);

  return (
    <>
      {moreOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="compass-fade absolute inset-0 bg-[var(--overlay)] backdrop-blur-[2px]"
            aria-label="Close more menu"
            onClick={onCloseMore}
          />
          <div
            ref={sheetRef}
            role="dialog"
            aria-modal="true"
            aria-label="More"
            className="compass-pop absolute inset-x-0 bottom-0 rounded-t-[var(--radius-lg)] border-t border-[var(--border)] bg-[var(--surface-raised)] px-3 pt-2 shadow-[var(--shadow-3)]"
            style={{
              paddingBottom:
                "calc(var(--bottom-nav-height) + env(safe-area-inset-bottom) + 0.75rem)",
            }}
          >
            <div
              aria-hidden
              className="mx-auto mb-2 h-1 w-9 rounded-full bg-[var(--border-strong)]"
            />
            <ul className="flex flex-col gap-0.5">
              {MORE_NAV.map((item) => {
                const active = isNavActive(pathname, item.href);
                const Icon = ICONS[item.href] ?? Sun;
                const count = "badgeKey" in item && item.badgeKey === "needsYou" ? needsYou : 0;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      onClick={onCloseMore}
                      className={`flex min-h-[52px] items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-[length:var(--text-body)] font-medium transition-colors duration-150 active:bg-[var(--pressed)] ${
                        active
                          ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                          : "text-[var(--ink)] hover:bg-[var(--hover)]"
                      }`}
                    >
                      <Icon
                        className={`h-5 w-5 shrink-0 ${active ? "" : "text-[var(--muted)]"}`}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{item.label}</span>
                        <span className="block truncate text-[length:var(--text-caption)] font-normal text-[var(--muted)]">
                          {item.hint}
                        </span>
                      </span>
                      {count > 0 ? (
                        <span
                          className="inline-flex min-w-5 items-center justify-center rounded-full bg-[var(--warning)] px-1.5 text-[length:var(--text-caption)] font-semibold text-[var(--on-status)]"
                          aria-label={`${count} waiting on you`}
                        >
                          {count > 9 ? "9+" : count}
                        </span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      ) : null}
      <nav
        aria-label="Mobile"
        className="fixed inset-x-0 bottom-0 z-50 border-t border-[var(--border)] bg-[color-mix(in_srgb,var(--surface)_92%,transparent)] backdrop-blur-md md:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        <ul className="grid grid-cols-5" style={{ minHeight: "var(--bottom-nav-height)" }}>
          {BOTTOM_NAV.map((item) => {
            const active = isNavActive(pathname, item.href);
            const Icon = ICONS[item.href] ?? Sun;
            return (
              <li key={item.href} className="min-w-0">
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  onClick={moreOpen ? onCloseMore : undefined}
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
          })}
          <li className="min-w-0">
            <button
              type="button"
              onClick={moreOpen ? onCloseMore : onOpenMore}
              aria-expanded={moreOpen}
              aria-label={needsYou > 0 ? `More, ${needsYou} waiting on you` : "More"}
              className={`relative flex h-full min-h-[48px] w-full flex-col items-center justify-center gap-0.5 px-1 text-[length:var(--text-caption)] leading-4 font-medium transition-colors duration-150 active:bg-[var(--pressed)] ${
                moreActive || moreOpen ? "text-[var(--accent-strong)]" : "text-[var(--muted)]"
              }`}
            >
              <span
                aria-hidden
                className={`absolute top-0 h-[3px] w-8 rounded-b-full bg-[var(--accent)] transition-opacity duration-150 ${moreActive || moreOpen ? "opacity-100" : "opacity-0"}`}
              />
              <span className="relative">
                <Menu className="h-5 w-5" aria-hidden />
                {needsYou > 0 ? (
                  <span className="absolute -top-1 -right-2 inline-flex min-w-4 items-center justify-center rounded-full bg-[var(--warning)] px-1 text-[10px] font-semibold text-[var(--on-status)] ring-2 ring-[var(--surface)]">
                    {needsYou > 9 ? "9+" : needsYou}
                  </span>
                ) : null}
              </span>
              More
            </button>
          </li>
        </ul>
      </nav>
    </>
  );
}
