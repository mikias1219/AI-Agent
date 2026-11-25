"use client";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function ErrorBlock({
  what,
  message,
  onRetry,
}: {
  what: string;
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm"
    >
      <span className="text-[var(--danger)]">
        Could not load {what}: {message}
      </span>
      <Button variant="secondary" className="min-h-11" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div
      className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
      aria-busy="true"
    >
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton
          key={i}
          heightClass={i === 0 ? "h-6" : "h-4"}
          className={i === 0 ? "w-1/2" : "w-full"}
        />
      ))}
    </div>
  );
}
