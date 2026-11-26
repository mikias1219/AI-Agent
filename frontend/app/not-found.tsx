import Link from "next/link";
import { buttonClassName } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-[var(--canvas)] px-6 text-center">
      <p className="text-sm font-medium text-[var(--muted)]">404</p>
      <h1
        className="text-[length:var(--text-display)] font-semibold text-[var(--ink)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        That page isn&apos;t here
      </h1>
      <p className="max-w-sm text-[length:var(--text-body)] text-[var(--muted)]">
        The link may be old or mistyped. Your day is one tap away.
      </p>
      <Link href="/" className={buttonClassName("primary", "md", "min-h-11")}>
        Back to Today
      </Link>
    </main>
  );
}
