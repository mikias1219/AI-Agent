import type { HTMLAttributes } from "react";

type SpinnerProps = HTMLAttributes<HTMLSpanElement> & {
  size?: "sm" | "md";
};

export function Spinner({ size = "md", className = "", ...props }: SpinnerProps) {
  const dim = size === "sm" ? "h-4 w-4 border-2" : "h-5 w-5 border-2";
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block animate-spin rounded-full border-[color-mix(in_srgb,currentColor_22%,transparent)] border-t-[var(--spinner,var(--accent))] ${dim} ${className}`}
      {...props}
    />
  );
}
