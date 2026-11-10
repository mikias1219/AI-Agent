import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowRight } from "lucide-react";

export type SummaryStatTile = {
  label: string;
  value: ReactNode;
  detail: string;
  href: string;
};

export type SummaryStatsProps = {
  tiles: SummaryStatTile[];
};

export function SummaryStats({ tiles }: SummaryStatsProps) {
  return (
    <section
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
      aria-label="Workspace summary"
    >
      {tiles.map((tile) => (
        <Link
          key={tile.label}
          href={tile.href}
          className="group rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 transition hover:border-[var(--accent)]/35 hover:shadow-sm sm:p-5"
        >
          <p className="text-xs font-medium text-[var(--muted)]">{tile.label}</p>
          <p
            className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {tile.value}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">{tile.detail}</p>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-[var(--accent)] opacity-0 transition group-hover:opacity-100">
            View <ArrowRight className="size-3.5" aria-hidden />
          </span>
        </Link>
      ))}
    </section>
  );
}
