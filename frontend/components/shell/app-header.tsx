"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Bell, Menu, MessageCircleQuestion, Pause, Play } from "lucide-react";
import { Avatar } from "@/components/ui/avatar";
import { IconButton } from "@/components/ui/icon-button";
import { StatusChip } from "@/components/ui/status-chip";
import { displayName } from "@/lib/auth/session";
import { getAgentControl, patchAgentControl } from "@/lib/api/agent-control";
import type { User } from "@/lib/api/types";
import { AutonomyChip } from "./autonomy-chip";
import { NotificationsDrawer } from "./notifications-drawer";
import { titleForPath } from "./nav";
import { ProfileMenu } from "./profile-menu";

export type AppHeaderProps = {
  user: User | null;
  sidebarOpen: boolean;
  needsYouCount?: number | null;
  onOpenSidebar: () => void;
  onOpenQuickAsk: () => void;
  onSignOut: () => Promise<void>;
};

export function AppHeader({
  user,
  sidebarOpen,
  needsYouCount = null,
  onOpenSidebar,
  onOpenQuickAsk,
  onSignOut,
}: AppHeaderProps) {
  const pathname = usePathname();
  const title = titleForPath(pathname);
  const name = displayName(user);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [shortcut, setShortcut] = useState("Ctrl K");
  const [paused, setPaused] = useState(false);
  const [controlReady, setControlReady] = useState(false);
  const [pauseBusy, setPauseBusy] = useState(false);
  const pending = needsYouCount && needsYouCount > 0 ? needsYouCount : 0;

  useEffect(() => {
    if (/Mac|iPhone|iPad/.test(navigator.platform)) setShortcut("⌘K");
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

  useEffect(() => {
    let cancelled = false;
    getAgentControl()
      .then((state) => {
        if (cancelled) return;
        setPaused(state.paused);
        setControlReady(true);
      })
      .catch(() => {
        if (!cancelled) setControlReady(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  async function togglePause() {
    setPauseBusy(true);
    try {
      const next = await patchAgentControl({ paused: !paused });
      setPaused(next.paused);
      setControlReady(true);
    } catch {
      /* Settings shows richer errors */
    } finally {
      setPauseBusy(false);
    }
  }

  const pauseLabel = !controlReady
    ? "Agent control unavailable"
    : paused
      ? "Resume agent"
      : "Pause agent";

  const bellLabel = pending > 0 ? `Notifications, ${pending} waiting` : "Notifications";

  return (
    <>
      <header
        className="sticky top-0 z-20 border-b border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur"
        style={{ minHeight: "var(--header-height)" }}
      >
        <div className="flex h-[var(--header-height)] items-center gap-3 px-4 sm:px-8">
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
            className="mx-auto hidden w-full max-w-[400px] items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-left text-sm text-[var(--muted)] transition hover:bg-[var(--canvas)] focus-visible:outline-2 focus-visible:outline-[var(--accent)] md:flex"
          >
            <MessageCircleQuestion className="h-4 w-4 shrink-0" aria-hidden />
            <span className="min-w-0 flex-1 truncate">Ask or tell AURA…</span>
            <kbd className="rounded border border-[var(--border)] bg-[var(--canvas)] px-1.5 text-xs">
              {shortcut}
            </kbd>
          </button>
          <div className="ml-auto flex items-center gap-2">
            <IconButton label="Quick ask" className="md:hidden" onClick={onOpenQuickAsk}>
              <MessageCircleQuestion className="h-4 w-4" aria-hidden />
            </IconButton>
            <AutonomyChip className="hidden sm:inline-flex" />
            {controlReady ? (
              <StatusChip tone={paused ? "warning" : "success"} className="hidden md:inline-flex">
                {paused ? "Paused" : "Listening"}
              </StatusChip>
            ) : null}
            <IconButton
              label={pauseLabel}
              title={pauseLabel}
              disabled={!controlReady || pauseBusy}
              onClick={() => void togglePause()}
              className="disabled:cursor-not-allowed disabled:opacity-50"
            >
              {paused ? (
                <Play className="h-4 w-4" aria-hidden />
              ) : (
                <Pause className="h-4 w-4" aria-hidden />
              )}
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
                <Bell className="h-4 w-4" aria-hidden />
              </IconButton>
              {pending > 0 ? (
                <span className="absolute -top-0.5 -right-0.5 inline-flex min-w-4 items-center justify-center rounded-full bg-[var(--warning)] px-1 text-[10px] font-semibold text-white">
                  {pending > 9 ? "9+" : pending}
                </span>
              ) : null}
            </span>
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                className="rounded-full"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                aria-label="Open profile menu"
                onClick={() => {
                  setBellOpen(false);
                  setMenuOpen((open) => !open);
                }}
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
      <NotificationsDrawer open={bellOpen} onClose={() => setBellOpen(false)} />
    </>
  );
}
