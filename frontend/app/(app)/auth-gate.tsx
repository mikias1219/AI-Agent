"use client";

import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { Spinner } from "@/components/ui/spinner";
import { isAuthenticated, sessionUser } from "@/lib/auth/session";
import { useAuth } from "@/features/auth/use-auth";

export function AuthGate({ children }: { children: ReactNode }) {
  const { status, loading, logout } = useAuth();

  if (loading) {
    return (
      <div
        className="flex min-h-dvh items-center justify-center"
        aria-live="polite"
        aria-busy="true"
      >
        <Spinner />
      </div>
    );
  }

  if (!isAuthenticated(status)) {
    redirect("/login");
  }

  return (
    <DashboardLayout user={sessionUser(status)} onSignOut={logout}>
      {children}
    </DashboardLayout>
  );
}
