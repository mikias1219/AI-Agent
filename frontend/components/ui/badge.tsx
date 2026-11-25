import type { HTMLAttributes, ReactNode } from "react";

export type BadgeTone = "neutral" | "accent" | "warning" | "success";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-[var(--subtle)] text-[var(--muted)] border-[var(--border)]",
  accent:
    "bg-[var(--accent-soft)] text-[var(--accent-strong)] border-[color-mix(in_srgb,var(--accent)_22%,var(--border))]",
  warning:
    "bg-[color-mix(in_srgb,var(--warning)_14%,var(--surface))] text-[var(--warning)] border-[color-mix(in_srgb,var(--warning)_28%,var(--border))]",
  success:
    "bg-[color-mix(in_srgb,var(--success)_14%,var(--surface))] text-[var(--success)] border-[color-mix(in_srgb,var(--success)_28%,var(--border))]",
};

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
  children: ReactNode;
};

export function Badge({ tone = "neutral", children, className = "", ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[length:var(--text-caption)] leading-4 font-medium ${toneClasses[tone]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
