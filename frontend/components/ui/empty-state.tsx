import type { ComponentType, ReactNode } from "react";

export type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  /** Tighter padding for empty tables and small cards. */
  compact?: boolean;
  /** Optional lucide-style icon shown above the title. */
  icon?: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
};

export function EmptyState({
  title,
  description,
  action,
  compact = false,
  icon: Icon,
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-2 rounded-[var(--radius)] border border-dashed border-[var(--border-strong)] bg-[color-mix(in_srgb,var(--subtle)_45%,var(--surface))] ${compact ? "px-4 py-6" : "px-6 py-12"} text-center`}
    >
      {Icon ? (
        <span className="mb-1 inline-flex h-10 w-10 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent-strong)]">
          <Icon className="h-5 w-5" aria-hidden />
        </span>
      ) : null}
      <h2
        className="text-[length:var(--text-title)] leading-[var(--leading-title)] font-semibold text-[var(--ink)]"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {title}
      </h2>
      {description ? (
        <p className="max-w-sm text-[length:var(--text-body)] leading-[var(--leading-body)] text-[var(--muted)]">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
