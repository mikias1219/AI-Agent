import { Suspense } from "react";
import { GooglePage } from "@/features/connections/google/google-page";
import { Spinner } from "@/components/ui/spinner";

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-[var(--muted)]">
          <Spinner size="sm" />
          Loading Google…
        </div>
      }
    >
      <GooglePage />
    </Suspense>
  );
}
