"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Bell, ChevronDown, Menu, Search } from "lucide-react";
import { Avatar } from "@/components/ui/avatar";
import { IconButton } from "@/components/ui/icon-button";
import { displayName } from "@/lib/auth/session";
import type { User } from "@/lib/api/types";
import { NotificationsDrawer } from "./notifications-drawer";
import { titleForPath } from "./nav";
import { ProfileMenu } from "./profile-menu";

export type AppHeaderProps = {
  user: User | null;
  ownerName?: string;
  photoSrc?: string;
  sidebarOpen: boolean;
  needsYouCount?: number | null;
  onOpenSidebar: () => void;
  onOpenQuickAsk: () => void;
  onSignOut: () => Promise<void>;
  /** Optional one-line context under the page title (hidden on phones). */
  subtitle?: string;
};

export function AppHeader({
  user,
  ownerName,
  photoSrc,
  sidebarOpen,
  needsYouCount = null,
  onOpenSidebar,
  onOpenQuickAsk,
  onSignOut,
  subtitle,
}: AppHeaderProps) {
  const pathname = usePathname();
  const title = titleForPath(pathname);
  const name = ownerName || displayName(user);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [shortcut, setShortcut] = useState("Ctrl K");
  const [scrolled, setScrolled] = useState(false);
  const pending = needsYouCount && needsYouCount > 0 ? needsYouCount : 0;

  useEffect(() => {
    if (/Mac|iPhone|iPad/.test(navigator.platform)) setShortcut("⌘K");
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
    setBellOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointer(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [menuOpen]);

  const bellLabel = pending > 0 ? `Notifications, ${pending} waiting` : "Notifications";

  return (
    <>
      <header
        data-scrolled={scrolled || undefined}
        className={`sticky top-0 z-20 border-b bg-[color-mix(in_srgb,var(--surface)_88%,transparent)] backdrop-blur-md transition-[border-color,box-shadow] duration-200 motion-reduce:transition-none ${
          scrolled ? "border-[var(--border)] shadow-[var(--shadow-1)]" : "border-[var(--border)]"
        }`}
        style={{ minHeight: "var(--header-height)" }}
      >
        <div className="flex h-[var(--header-height)] items-center gap-3 px-3 sm:px-8">
          <IconButton
            label="Open menu"
            className="md:hidden"
            aria-expanded={sidebarOpen}
            aria-controls="app-sidebar"
            onClick={onOpenSidebar}
          >
            <Menu className="h-5 w-5" aria-hidden />
          </IconButton>

          <div className="min-w-0 flex-1 md:flex-none md:basis-48">
            <p className="truncate text-[length:var(--text-title)] leading-6 font-semibold tracking-[-0.01em] text-[var(--ink)]">
              {title}
            </p>
            {subtitle ? (
              <p className="hidden truncate text-[length:var(--text-caption)] leading-4 text-[var(--muted)] sm:block">
                {subtitle}
              </p>
            ) : null}
          </div>

          <button
            type="button"
            onClick={onOpenQuickAsk}
            aria-label="Open command palette"
            aria-keyshortcuts="Control+K Meta+K"
            className="mx-auto hidden h-10 w-full max-w-[460px] items-center gap-2.5 rounded-[var(--radius)] border border-transparent bg-[var(--subtle)] px-3 text-left text-[length:var(--text-body)] text-[var(--muted)] transition-[background-color,border-color,box-shadow] duration-150 hover:border-[var(--border-strong)] hover:bg-[var(--surface)] focus-visible:outline-2 focus-visible:outline-[var(--accent)] motion-reduce:transition-none md:flex"
          >
            <Search className="h-4 w-4 shrink-0" aria-hidden />
            <span className="min-w-0 flex-1 truncate">Ask, create, or go to…</span>
            <kbd className="rounded-md border border-[var(--border-strong)] bg-[var(--surface)] px-1.5 py-0.5 font-sans text-[length:var(--text-caption)] leading-4 font-medium text-[var(--muted)] shadow-[var(--shadow-1)]">
              {shortcut}
            </kbd>
          </button>

          <div className="ml-auto flex items-center gap-1">
            <IconButton label="Open command palette" className="md:hidden" onClick={onOpenQuickAsk}>
              <Search className="h-5 w-5" aria-hidden />
            </IconButton>
            <span className="relative inline-flex">
              <IconButton
                label={bellLabel}
                aria-expanded={bellOpen}
                onClick={() => {
                  setMenuOpen(false);
                  setBellOpen(true);
                }}
              >
                <Bell className="h-5 w-5" aria-hidden />
              </IconButton>
              {pending > 0 ? (
                <span
                  aria-hidden
                  className="pointer-events-none absolute top-1 right-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--warning)] px-1 text-[10px] leading-none font-semibold text-[var(--on-status)] ring-2 ring-[var(--surface)]"
                >
                  {pending > 9 ? "9+" : pending}
                </span>
              ) : null}
            </span>
            <div className="relative ml-1" ref={menuRef}>
              <button
                type="button"
                className="flex h-10 items-center gap-1 rounded-full pr-1.5 pl-1 transition-colors duration-150 hover:bg-[var(--hover)] active:bg-[var(--pressed)] motion-reduce:transition-none"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                aria-label="Open profile menu"
                onClick={() => {
                  setBellOpen(false);
                  setMenuOpen((open) => !open);
                }}
              >
                <Avatar name={name} src={photoSrc} size="sm" />
                <ChevronDown
                  className={`hidden h-4 w-4 text-[var(--muted)] transition-transform duration-150 motion-reduce:transition-none sm:block ${menuOpen ? "rotate-180" : ""}`}
                  aria-hidden
                />
              </button>
              <ProfileMenu
                user={user}
                ownerName={name}
                photoSrc={photoSrc}
                open={menuOpen}
                onClose={() => setMenuOpen(false)}
                onSignOut={onSignOut}
              />
            </div>
          </div>
        </div>
      </header>
      <NotificationsDrawer open={bellOpen} onClose={() => setBellOpen(false)} />
    </>
  );
}
