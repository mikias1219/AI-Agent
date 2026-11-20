import type { ReactNode } from "react";

export type BannerTone = "neutral" | "success" | "warning" | "danger" | "info";

export type BannerProps = {
  tone?: BannerTone;
  children: ReactNode;
  className?: string;
  role?: "status" | "alert";
};

const toneClass: Record<BannerTone, string> = {
  neutral: "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)]",
  success:
    "border-[color-mix(in_srgb,var(--success)_35%,var(--border))] bg-[color-mix(in_srgb,var(--success)_10%,var(--surface))] text-[var(--ink)]",
  warning:
    "border-[color-mix(in_srgb,var(--warning)_35%,var(--border))] bg-[color-mix(in_srgb,var(--warning)_10%,var(--surface))] text-[var(--ink)]",
  danger:
    "border-[color-mix(in_srgb,var(--danger)_35%,var(--border))] bg-[color-mix(in_srgb,var(--danger)_10%,var(--surface))] text-[var(--ink)]",
  info: "border-[color-mix(in_srgb,var(--info)_35%,var(--border))] bg-[color-mix(in_srgb,var(--info)_10%,var(--surface))] text-[var(--ink)]",
};

export function Banner({
  tone = "neutral",
  children,
  className = "",
  role = "status",
}: BannerProps) {
  return (
    <div
      role={role}
      className={`rounded-[var(--radius)] border px-4 py-3 text-[length:var(--text-body)] leading-[var(--leading-body)] ${toneClass[tone]} ${className}`.trim()}
    >
      {children}
    </div>
  );
}
