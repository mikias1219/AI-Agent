import type { HTMLAttributes, ReactNode } from "react";

export type BadgeTone = "neutral" | "accent" | "warning" | "success";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-[var(--canvas)] text-[var(--muted)] border-[var(--border)]",
  accent: "bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent-soft)]",
  warning: "bg-[#fef3eb] text-[var(--warning)] border-[#f9dbaf]",
  success: "bg-[#ecfdf3] text-[var(--success)] border-[#abefc6]",
};

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
  children: ReactNode;
};

export function Badge({ tone = "neutral", children, className = "", ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${toneClasses[tone]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
