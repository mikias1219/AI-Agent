import { Suspense } from "react";
import { LearnPage } from "@/features/learn/learn-page";

export default function Page() {
  return (
    <Suspense fallback={<p className="text-sm text-[var(--muted)]">Loading…</p>}>
      <LearnPage />
    </Suspense>
  );
}
