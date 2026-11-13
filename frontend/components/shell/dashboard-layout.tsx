"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { listApprovals } from "@/lib/api/approvals";
import { getInbox } from "@/lib/api/inbox";
import { getAgentControl } from "@/lib/api/agent-control";
import { badgeCount } from "@/features/inbox/inbox-logic";
import type { User } from "@/lib/api/types";
import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";
import { QuickAskDrawer } from "./quick-ask-drawer";

const APPROVAL_POLL_MS = 3_000;

export type DashboardLayoutProps = {
  user: User | null;
  onSignOut: () => Promise<void>;
  children: ReactNode;
};

export function DashboardLayout({ user, onSignOut, children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [quickAskOpen, setQuickAskOpen] = useState(false);
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

  useEffect(() => {
    setSidebarOpen(false);
    setQuickAskOpen(false);
  }, [pathname]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSidebarOpen(false);
        setQuickAskOpen(true);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    refreshApprovals();
    refreshControl();
    const id = window.setInterval(() => {
      refreshApprovals();
      refreshControl();
    }, APPROVAL_POLL_MS);
    return () => window.clearInterval(id);
  }, [refreshApprovals, refreshControl]);

  return (
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
              setQuickAskOpen(true);
            }}
            onSignOut={onSignOut}
          />
          <main key={pathname} className="aura-enter flex-1 px-4 py-7 sm:px-8">
            <div className="mx-auto w-full max-w-6xl">{children}</div>
          </main>
        </div>
      </div>
      <QuickAskDrawer open={quickAskOpen} onClose={() => setQuickAskOpen(false)} />
    </div>
  );
}
