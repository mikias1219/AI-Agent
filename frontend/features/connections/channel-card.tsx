import Link from "next/link";
import type { ReactNode } from "react";
import { Badge, type BadgeTone } from "@/components/ui/badge";

export type ChannelCardProps = {
  href: string;
  name: string;
  description: string;
  badge: string;
  tone: BadgeTone;
  icon: ReactNode;
};

export function ChannelCard({
  href,
  name,
  description,
  badge,
  tone,
  icon,
}: ChannelCardProps) {
  return (
    <li>
      <Link
        href={href}
        className="flex h-full flex-col gap-4 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5 transition hover:border-[var(--accent)]/40"
      >
        <span className="flex items-start justify-between gap-3">
          <span className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
              {icon}
            </span>
            <h2 className="text-base font-semibold text-[var(--ink)]">{name}</h2>
          </span>
          <Badge tone={tone}>{badge}</Badge>
        </span>
        <p className="text-sm leading-6 text-[var(--muted)]">{description}</p>
      </Link>
    </li>
  );
}
