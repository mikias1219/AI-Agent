import type { HTMLAttributes } from "react";

export type SkeletonProps = HTMLAttributes<HTMLDivElement> & {
  /** Optional fixed height utility, e.g. "h-4". */
  heightClass?: string;
};

/** Loading placeholder. Prefer this over a spinner for list and card layouts. */
export function Skeleton({ className = "", heightClass = "h-4", ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={`animate-pulse rounded-md bg-[color-mix(in_srgb,var(--muted)_18%,var(--surface))] ${heightClass} ${className}`.trim()}
      {...props}
    />
  );
}

export function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" aria-live="polite">
      {Array.from({ length: count }, (_, index) => (
        <Skeleton key={index} heightClass="h-12" className="w-full" />
      ))}
    </div>
  );
}
