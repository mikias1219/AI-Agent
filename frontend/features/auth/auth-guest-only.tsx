"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/components/ui/spinner";
import { isAuthenticated } from "@/lib/auth/session";
import { useAuth } from "./use-auth";

export function AuthGuestOnly({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { status, loading } = useAuth();

  useEffect(() => {
    if (!loading && isAuthenticated(status)) {
      router.replace("/");
    }
  }, [loading, status, router]);

  if (loading || isAuthenticated(status)) {
    return (
      <div className="flex min-h-[12rem] items-center justify-center" aria-live="polite" aria-busy={loading}>
        <Spinner />
      </div>
    );
  }

  return <>{children}</>;
}
