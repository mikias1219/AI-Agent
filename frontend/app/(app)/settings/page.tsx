import { Suspense } from "react";
import { SettingsPage } from "@/features/settings/settings-page";
import { Spinner } from "@/components/ui/spinner";

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-[var(--muted)]">
          <Spinner size="sm" />
          Loading settings…
        </div>
      }
    >
      <SettingsPage />
    </Suspense>
  );
}
