import type { HTMLAttributes, ReactNode } from "react";

export type StatusChipTone = "neutral" | "accent" | "warning" | "success" | "danger";

const toneClasses: Record<StatusChipTone, string> = {
  neutral:
    "border-[var(--border)] bg-[var(--canvas)] text-[var(--muted)]",
  accent:
    "border-[var(--accent-soft)] bg-[var(--accent-soft)] text-[var(--accent)]",
  warning:
    "border-[color-mix(in_srgb,var(--warning)_28%,var(--border))] bg-[color-mix(in_srgb,var(--warning)_14%,var(--surface))] text-[var(--warning)]",
  success:
    "border-[color-mix(in_srgb,var(--success)_28%,var(--border))] bg-[color-mix(in_srgb,var(--success)_14%,var(--surface))] text-[var(--success)]",
  danger:
    "border-[color-mix(in_srgb,var(--danger)_28%,var(--border))] bg-[color-mix(in_srgb,var(--danger)_12%,var(--surface))] text-[var(--danger)]",
};

export type StatusChipProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: StatusChipTone;
  children: ReactNode;
};

export function StatusChip({
  tone = "neutral",
  children,
  className = "",
  ...props
}: StatusChipProps) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${toneClasses[tone]} ${className}`.trim()}
      {...props}
    >
      {children}
    </span>
  );
}
