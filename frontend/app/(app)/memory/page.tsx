import { Suspense } from "react";
import { MemoryPage } from "@/features/memory/memory-page";

export default function Page() {
  return (
    <Suspense fallback={<p className="text-sm text-[var(--muted)]">Loading memory…</p>}>
      <MemoryPage />
    </Suspense>
  );
}
