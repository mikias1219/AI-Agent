"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { listApprovals } from "@/lib/api/tasks";
import type { User } from "@/lib/api/types";
import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";
import { NotificationsDrawer } from "./notifications-drawer";

const APPROVAL_POLL_MS = 20_000;

export type DashboardLayoutProps = {
  user: User | null;
  onSignOut: () => Promise<void>;
  children: ReactNode;
};

export function DashboardLayout({ user, onSignOut, children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [approvalCount, setApprovalCount] = useState<number | null>(null);
  const [approvalsUnavailable, setApprovalsUnavailable] = useState(false);
  const [approvalRefreshKey, setApprovalRefreshKey] = useState(0);

  const refreshApprovals = useCallback(() => {
    listApprovals()
      .then((rows) => {
        const pending = rows.filter((r) => r.actionable);
        setApprovalCount(pending.length);
        setApprovalsUnavailable(false);
        setApprovalRefreshKey((k) => k + 1);
      })
      .catch(() => {
        setApprovalCount(null);
        setApprovalsUnavailable(true);
      });
  }, []);

  useEffect(() => {
    setSidebarOpen(false);
    setNotificationsOpen(false);
  }, [pathname]);

  useEffect(() => {
    refreshApprovals();
    const id = window.setInterval(() => {
      refreshApprovals();
    }, APPROVAL_POLL_MS);
    return () => window.clearInterval(id);
  }, [refreshApprovals]);

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
        <AppSidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <AppHeader
            user={user}
            approvalCount={approvalCount}
            notificationsOpen={notificationsOpen}
            sidebarOpen={sidebarOpen}
            onOpenSidebar={() => setSidebarOpen(true)}
            onOpenNotifications={() => {
              setSidebarOpen(false);
              setNotificationsOpen(true);
            }}
            onSignOut={onSignOut}
          />
          <main key={pathname} className="aura-enter flex-1 px-4 py-6 sm:px-8 sm:py-8">
            {children}
          </main>
        </div>
      </div>
      <NotificationsDrawer
        open={notificationsOpen}
        onClose={() => setNotificationsOpen(false)}
        approvalsUnavailable={approvalsUnavailable}
        refreshKey={approvalRefreshKey}
        onApprovalChanged={refreshApprovals}
      />
    </div>
  );
}
