import type { ButtonHTMLAttributes } from "react";
import { Spinner } from "./spinner";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-[var(--accent)] text-white hover:brightness-110 border border-transparent",
  secondary:
    "bg-[var(--surface)] text-[var(--ink)] border border-[var(--border)] hover:bg-[var(--canvas)]",
  ghost: "bg-transparent text-[var(--ink)] border border-transparent hover:bg-[var(--accent-soft)]",
  danger: "bg-[var(--danger)] text-white hover:brightness-110 border border-transparent",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm gap-1.5",
  md: "px-4 py-2.5 text-sm gap-2",
};

export function buttonClassName(
  variant: ButtonVariant = "primary",
  size: ButtonSize = "md",
  className = "",
) {
  return `inline-flex items-center justify-center rounded-[var(--radius)] font-medium transition disabled:opacity-50 ${variantClasses[variant]} ${sizeClasses[size]} ${className}`.trim();
}

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <button
      type={type}
      disabled={isDisabled}
      className={buttonClassName(variant, size, className)}
      {...props}
    >
      {loading ? <Spinner size="sm" /> : null}
      {children}
    </button>
  );
}
