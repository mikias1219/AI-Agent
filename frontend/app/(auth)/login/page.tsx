import { Suspense } from "react";
import { LoginForm } from "@/features/auth/login-form";
import { LoginSuccessNote } from "@/features/auth/login-success-note";

export default function LoginPage() {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h2
          className="text-xl font-semibold text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Welcome back
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Sign in to your workspace.</p>
      </header>

      <Suspense fallback={<LoginForm />}>
        <LoginSuccessNote />
      </Suspense>
    </div>
  );
}
