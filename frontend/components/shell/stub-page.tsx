import type { ReactNode } from "react";
import { EmptyState } from "@/components/ui/empty-state";

export type StubPageProps = {
  title: string;
  intro: string;
  emptyTitle: string;
  emptyDescription: string;
  action?: ReactNode;
};

/** Honest placeholder for screens that are not wired to data yet: no sample rows, no invented facts. */
export function StubPage({ title, intro, emptyTitle, emptyDescription, action }: StubPageProps) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header>
        <h2
          className="text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {title}
        </h2>
        <p className="mt-2 text-sm text-[var(--muted)]">{intro}</p>
      </header>
      <EmptyState title={emptyTitle} description={emptyDescription} action={action} />
    </div>
  );
}
