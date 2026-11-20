"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { listApprovals } from "@/lib/api/approvals";
import { getInbox } from "@/lib/api/inbox";
import { getAgentControl } from "@/lib/api/agent-control";
import { badgeCount } from "@/features/inbox/inbox-logic";
import type { User } from "@/lib/api/types";
import { usePolling } from "@/lib/client-cache/use-polling";
import { ToastProvider } from "@/components/ui/toast";
import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";
import { BottomNav } from "./bottom-nav";
import { CommandPalette } from "./command-palette";
import { QuickAskDrawer } from "./quick-ask-drawer";

const APPROVAL_POLL_MS = 5_000;

export type DashboardLayoutProps = {
  user: User | null;
  onSignOut: () => Promise<void>;
  children: ReactNode;
};

export function DashboardLayout({ user, onSignOut, children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [quickAskOpen, setQuickAskOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [approvalCount, setApprovalCount] = useState<number | null>(null);
  const [agentPaused, setAgentPaused] = useState<boolean | null>(null);

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
    setSidebarOpen(false);
    setQuickAskOpen(false);
    setPaletteOpen(false);
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

  usePolling(refreshShell, APPROVAL_POLL_MS);

  return (
    <ToastProvider>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[200] focus:rounded-[var(--radius)] focus:bg-[var(--surface)] focus:px-3 focus:py-2 focus:text-sm focus:text-[var(--ink)] focus:shadow-md"
      >
        Skip to content
      </a>
      <div className="min-h-dvh">
        {sidebarOpen ? (
          <button
            type="button"
            className="fixed inset-0 z-30 bg-[var(--ink)]/30 md:hidden"
            aria-label="Close menu"
            onClick={() => setSidebarOpen(false)}
          />
        ) : null}
        <div className="flex min-h-dvh">
          <AppSidebar
            open={sidebarOpen}
            onNavigate={() => setSidebarOpen(false)}
            needsYouCount={approvalCount}
            agentPaused={agentPaused}
          />
          <div className="flex min-w-0 flex-1 flex-col">
            <AppHeader
              user={user}
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
              className="aura-enter flex-1 px-4 pt-7 pb-[calc(var(--bottom-nav-height)+1.5rem)] sm:px-8 md:pb-7"
            >
              <div className="mx-auto w-full max-w-[var(--content-width)]">{children}</div>
            </main>
          </div>
        </div>
        <BottomNav
          needsYouCount={approvalCount}
          onOpenMore={() => {
            setQuickAskOpen(false);
            setPaletteOpen(false);
            setSidebarOpen(true);
          }}
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
