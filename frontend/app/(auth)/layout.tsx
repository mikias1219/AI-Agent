import type { ReactNode } from "react";
import { AuthGuestOnly } from "@/features/auth/auth-guest-only";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col items-center px-4 py-10 sm:py-14">
      <div className="mb-10 text-center">
        <p
          className="text-xs font-medium tracking-[0.22em] text-[var(--muted)] uppercase"
          style={{ fontFamily: "var(--font-ui)" }}
        >
          Personal agent
        </p>
        <h1
          className="mt-2 text-5xl font-semibold tracking-tight text-[var(--ink)] sm:text-6xl"
          style={{ fontFamily: "var(--font-display)" }}
        >
          AURA
        </h1>
      </div>

      <AuthCard>
        <AuthGuestOnly>{children}</AuthGuestOnly>
      </AuthCard>
    </div>
  );
}

function AuthCard({ children }: { children: ReactNode }) {
  return (
    <div className="w-full max-w-md rounded-[calc(var(--radius)+4px)] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm sm:p-8">
      {children}
    </div>
  );
}
