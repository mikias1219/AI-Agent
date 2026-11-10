import { Suspense } from "react";
import { ActivityPage } from "@/features/activity/activity-page";
import { Spinner } from "@/components/ui/spinner";

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-[var(--muted)]">
          <Spinner size="sm" />
          Loading activity…
        </div>
      }
    >
      <ActivityPage />
    </Suspense>
  );
}
