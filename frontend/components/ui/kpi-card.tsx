import type { ComponentType, ReactNode } from "react";
import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

export type KpiCardProps = {
  label: string;
  value: string | number;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  /** Percent change vs the previous period; null hides the trend. */
  delta?: number | null;
  /** Whether an increase is good. Controls the trend colour. */
  upIsGood?: boolean;
  hint?: string;
  href?: string;
  /** Optional sparkline. */
  trend?: ReactNode;
  tone?: "default" | "warning";
};

export function KpiCard({
  label,
  value,
  icon: Icon,
  delta = null,
  upIsGood = true,
  hint,
  href,
  trend,
  tone = "default",
}: KpiCardProps) {
  const good = delta === null || delta === 0 ? null : delta > 0 === upIsGood;
  const TrendIcon =
    delta === null || delta === 0 ? Minus : delta > 0 ? ArrowUpRight : ArrowDownRight;
  const body = (
    <div className="flex h-full flex-col gap-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[length:var(--text-small)] font-medium tracking-[0.01em] text-[var(--muted)]">
          {label}
        </span>
        <span
          className={`inline-flex h-8 w-8 items-center justify-center rounded-lg ${
            tone === "warning"
              ? "bg-[color-mix(in_srgb,var(--warning)_14%,var(--surface))] text-[var(--warning)]"
              : "bg-[var(--accent-soft)] text-[var(--accent)]"
          }`}
        >
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      </div>
      <div className="flex items-end justify-between gap-2">
        <p className="text-[length:var(--text-display)] leading-none font-semibold tracking-[-0.02em] text-[var(--ink)] tabular-nums">
          {value}
        </p>
        {trend}
      </div>
      <p className="flex min-h-4 items-center gap-1 text-[length:var(--text-caption)] text-[var(--muted)]">
        {delta !== null ? (
          <span
            className={`inline-flex items-center gap-0.5 font-medium ${
              good === null ? "" : good ? "text-[var(--success)]" : "text-[var(--danger)]"
            }`}
          >
            <TrendIcon className="h-3 w-3" aria-hidden />
            {delta > 0 ? "+" : ""}
            {delta}%
          </span>
        ) : null}
        {hint ? <span className="truncate">{hint}</span> : null}
      </p>
    </div>
  );
  const frame =
    "block rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-1)] transition-[border-color,box-shadow] duration-150 motion-reduce:transition-none";
  return href ? (
    <Link
      href={href}
      className={`${frame} hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-2)]`}
    >
      {body}
    </Link>
  ) : (
    <div className={frame}>{body}</div>
  );
}
