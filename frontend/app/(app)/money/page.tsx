import { Suspense } from "react";
import { MoneyPage } from "@/features/money/money-page";

export default function Page() {
  return (
    <Suspense fallback={<p className="text-sm text-[var(--muted)]">Loading…</p>}>
      <MoneyPage />
    </Suspense>
  );
}
