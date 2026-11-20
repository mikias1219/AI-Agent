import type { SelectHTMLAttributes } from "react";

const baseClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[length:var(--text-body)] leading-[var(--leading-body)] text-[var(--ink)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)] disabled:opacity-60";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export function Select({ className = "", children, ...props }: SelectProps) {
  return (
    <select className={`${baseClass} ${className}`.trim()} {...props}>
      {children}
    </select>
  );
}
