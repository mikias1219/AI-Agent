"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { listApprovals } from "@/lib/api/approvals";
import { getInbox } from "@/lib/api/inbox";
import { getAgentControl } from "@/lib/api/agent-control";
import { getToday } from "@/lib/api/today";
import { badgeCount } from "@/features/inbox/inbox-logic";
import { displayName } from "@/lib/auth/session";
import { getProfile, photoSrc, PROFILE_CHANGED_EVENT, type Profile } from "@/lib/api/profile";
import type { User } from "@/lib/api/types";
import { usePolling } from "@/lib/client-cache/use-polling";
import { ToastProvider } from "@/components/ui/toast";
import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";
import { BottomNav } from "./bottom-nav";
import { QUICK_ADD_EVENT, QuickAddSheet, type QuickKind } from "./quick-add-sheet";
import { CommandPalette } from "./command-palette";
import { QuickAskDrawer } from "./quick-ask-drawer";
import type { NavCounts } from "./nav";

const APPROVAL_POLL_MS = 5_000;

export type DashboardLayoutProps = {
  user: User | null;
  onSignOut: () => Promise<void>;
  children: ReactNode;
};

export function DashboardLayout({ user, onSignOut, children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [quickAskOpen, setQuickAskOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [approvalCount, setApprovalCount] = useState<number | null>(null);
  const [agentPaused, setAgentPaused] = useState<boolean | null>(null);
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const [navCounts, setNavCounts] = useState<NavCounts>({});
  const [quickAddKind, setQuickAddKind] = useState<QuickKind>("expense");

  // Any page can open the one Add sheet on a given kind: window.dispatchEvent(new
  // CustomEvent(QUICK_ADD_EVENT, { detail: "income" })).
  useEffect(() => {
    function onQuickAdd(event: Event) {
      const detail = (event as CustomEvent<QuickKind | undefined>).detail;
      setQuickAddKind(detail ?? "expense");
      setQuickAddOpen(true);
    }
    window.addEventListener(QUICK_ADD_EVENT, onQuickAdd);
    return () => window.removeEventListener(QUICK_ADD_EVENT, onQuickAdd);
  }, []);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [photoVersion, setPhotoVersion] = useState(() => Date.now());

  const refreshApprovals = useCallback(() => {
    getInbox("open")
      .then((inbox) => setApprovalCount(inbox.counts.open))
      .catch(() =>
        listApprovals()
          .then((rows) =>
            setApprovalCount(badgeCount(null, rows.filter((r) => r.actionable).length)),
          )
          .catch(() => setApprovalCount(null)),
      );
  }, []);

  const refreshControl = useCallback(() => {
    getAgentControl()
      .then((state) => setAgentPaused(state.paused))
      .catch(() => setAgentPaused(null));
  }, []);

  const refreshShell = useCallback(() => {
    refreshApprovals();
    refreshControl();
  }, [refreshApprovals, refreshControl]);

  useEffect(() => {
    let cancelled = false;
    function loadProfile(bypass: boolean) {
      getProfile(bypass)
        .then((next) => {
          if (cancelled) return;
          setProfile(next);
          if (bypass) setPhotoVersion(Date.now());
        })
        .catch(() => {
          /* the shell falls back to the signed-in name and initials */
        });
    }
    loadProfile(false);
    const onChanged = () => loadProfile(true);
    window.addEventListener(PROFILE_CHANGED_EVENT, onChanged);
    return () => {
      cancelled = true;
      window.removeEventListener(PROFILE_CHANGED_EVENT, onChanged);
    };
  }, []);

  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem("compass.sidebar") === "collapsed");
    } catch {
      /* storage unavailable: stay expanded */
    }
  }, []);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem("compass.sidebar", next ? "collapsed" : "expanded");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  useEffect(() => {
    setSidebarOpen(false);
    setQuickAskOpen(false);
    setPaletteOpen(false);
  }, [pathname]);

  // Plan and Learn counts come from the Today payload; refreshed when the page changes.
  useEffect(() => {
    let cancelled = false;
    getToday()
      .then((today) => {
        if (cancelled) return;
        setNavCounts({
          tasksLeft: today.day?.summary?.open ?? null,
          wordsDue: today.life?.learn?.due ?? null,
        });
      })
      .catch(() => {
        /* counts are a hint; the sidebar works without them */
      });
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSidebarOpen(false);
        setQuickAskOpen(false);
        setPaletteOpen(true);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const ownerName = profile?.name?.trim() || displayName(user);
  const avatarSrc = photoSrc(profile, photoVersion);

  usePolling(refreshShell, APPROVAL_POLL_MS);

  return (
    <ToastProvider>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[200] focus:rounded-[var(--radius)] focus:bg-[var(--surface)] focus:px-3 focus:py-2 focus:text-sm focus:text-[var(--ink)] focus:shadow-[var(--shadow-2)]"
      >
        Skip to content
      </a>
      <div className="min-h-dvh">
        {sidebarOpen ? (
          <button
            type="button"
            className="compass-fade fixed inset-0 z-30 bg-[var(--overlay)] backdrop-blur-[2px] md:hidden"
            aria-label="Close menu"
            onClick={() => setSidebarOpen(false)}
          />
        ) : null}
        <div className="flex min-h-dvh">
          <AppSidebar
            open={sidebarOpen}
            onNavigate={() => setSidebarOpen(false)}
            collapsed={collapsed}
            onToggleCollapsed={toggleCollapsed}
            onQuickAdd={() => {
              setQuickAddKind("expense");
              setQuickAddOpen(true);
            }}
            counts={navCounts}
            needsYouCount={approvalCount}
            agentPaused={agentPaused}
            ownerName={ownerName}
            photoSrc={avatarSrc}
          />
          <div className="flex min-w-0 flex-1 flex-col">
            <AppHeader
              user={user}
              ownerName={ownerName}
              photoSrc={avatarSrc}
              sidebarOpen={sidebarOpen}
              needsYouCount={approvalCount}
              onOpenSidebar={() => setSidebarOpen(true)}
              onOpenQuickAsk={() => {
                setSidebarOpen(false);
                setQuickAskOpen(false);
                setPaletteOpen(true);
              }}
              onSignOut={onSignOut}
            />
            <main
              id="main-content"
              key={pathname}
              tabIndex={-1}
              className="compass-enter flex-1 px-4 pt-6 pb-[calc(var(--bottom-nav-height)+env(safe-area-inset-bottom)+1.5rem)] sm:px-8 sm:pt-8 md:pb-10"
            >
              <div className="mx-auto w-full max-w-[var(--content-width)]">{children}</div>
            </main>
          </div>
        </div>
        <BottomNav
          onQuickAdd={() => {
            setQuickAddKind("expense");
            setQuickAddOpen(true);
          }}
        />
        <QuickAddSheet
          open={quickAddOpen}
          initial={quickAddKind}
          onClose={() => setQuickAddOpen(false)}
        />
        <CommandPalette
          open={paletteOpen}
          onClose={() => setPaletteOpen(false)}
          onOpenQuickAsk={() => {
            setPaletteOpen(false);
            setQuickAskOpen(true);
          }}
        />
        <QuickAskDrawer open={quickAskOpen} onClose={() => setQuickAskOpen(false)} />
      </div>
    </ToastProvider>
  );
}
