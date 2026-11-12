"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, MessageCircleQuestion, Pause } from "lucide-react";
import { Avatar } from "@/components/ui/avatar";
import { IconButton } from "@/components/ui/icon-button";
import { displayName } from "@/lib/auth/session";
import type { User } from "@/lib/api/types";
import { AutonomyChip } from "./autonomy-chip";
import { titleForPath } from "./nav";
import { ProfileMenu } from "./profile-menu";

/** Pause needs the agent-control API (Task 2); until then the button stays disabled. */
export const PAUSE_UNAVAILABLE_HINT = "Coming with agent control";

export type AppHeaderProps = {
  user: User | null;
  sidebarOpen: boolean;
  onOpenSidebar: () => void;
  onOpenQuickAsk: () => void;
  onSignOut: () => Promise<void>;
};

export function AppHeader({
  user,
  sidebarOpen,
  onOpenSidebar,
  onOpenQuickAsk,
  onSignOut,
}: AppHeaderProps) {
  const pathname = usePathname();
  const title = titleForPath(pathname);
  const name = displayName(user);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [shortcut, setShortcut] = useState("Ctrl K");

  useEffect(() => {
    if (/Mac|iPhone|iPad/.test(navigator.platform)) setShortcut("⌘K");
  }, []);

  useEffect(() => {
    setMenuOpen(false);
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

  return (
    <header className="sticky top-0 z-20 border-b border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur">
      <div className="flex items-center gap-3 px-4 py-3">
        <IconButton
          label="Open menu"
          className="md:hidden"
          aria-expanded={sidebarOpen}
          aria-controls="app-sidebar"
          onClick={onOpenSidebar}
        >
          <Menu className="h-4 w-4" aria-hidden />
        </IconButton>
        <h1
          className="min-w-0 flex-1 truncate text-xl font-semibold tracking-tight text-[var(--ink)] sm:flex-none"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {title}
        </h1>
        <button
          type="button"
          onClick={onOpenQuickAsk}
          aria-label="Quick ask"
          aria-keyshortcuts="Control+K Meta+K"
          className="mx-auto hidden w-full max-w-sm items-center gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-left text-sm text-[var(--muted)] transition hover:bg-[var(--canvas)] focus-visible:outline-2 focus-visible:outline-[var(--accent)] md:flex"
        >
          <MessageCircleQuestion className="h-4 w-4 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1 truncate">Ask AURA…</span>
          <kbd className="rounded border border-[var(--border)] bg-[var(--canvas)] px-1.5 text-xs">
            {shortcut}
          </kbd>
        </button>
        <div className="ml-auto flex items-center gap-2">
          <IconButton label="Quick ask" className="md:hidden" onClick={onOpenQuickAsk}>
            <MessageCircleQuestion className="h-4 w-4" aria-hidden />
          </IconButton>
          <AutonomyChip className="hidden sm:inline-flex" />
          <span title={PAUSE_UNAVAILABLE_HINT} className="inline-flex">
            <IconButton
              label={`Pause agent. ${PAUSE_UNAVAILABLE_HINT}`}
              title={PAUSE_UNAVAILABLE_HINT}
              disabled
              className="disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Pause className="h-4 w-4" aria-hidden />
            </IconButton>
          </span>
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              className="rounded-full"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-label="Open profile menu"
              onClick={() => setMenuOpen((open) => !open)}
            >
              <Avatar name={name} size="sm" />
            </button>
            <ProfileMenu
              user={user}
              open={menuOpen}
              onClose={() => setMenuOpen(false)}
              onSignOut={onSignOut}
            />
          </div>
        </div>
      </div>
    </header>
  );
}
