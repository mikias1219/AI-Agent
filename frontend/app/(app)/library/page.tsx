import { Suspense } from "react";
import { LibraryPage } from "@/features/library/library-page";

export default function Page() {
  return (
    <Suspense fallback={<p className="text-sm text-[var(--muted)]">Loading…</p>}>
      <LibraryPage />
    </Suspense>
  );
}
