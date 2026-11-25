import { Suspense } from "react";
import { SettingsPage } from "@/features/settings/settings-page";
import { Skeleton } from "@/components/ui/skeleton";

export default function Page() {
  return (
    <Suspense fallback={<Skeleton heightClass="h-40" className="mx-auto w-full max-w-[720px]" />}>
      <SettingsPage />
    </Suspense>
  );
}
