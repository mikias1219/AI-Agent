import type { ReactNode } from "react";

export type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius)] border border-dashed border-[var(--border)] bg-[var(--surface)] px-6 py-12 text-center">
      <h2
        className="text-lg font-semibold text-[var(--ink)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {title}
      </h2>
      {description ? <p className="max-w-sm text-sm text-[var(--muted)]">{description}</p> : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
