import type { ButtonHTMLAttributes } from "react";
import { Spinner } from "./spinner";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--accent)] text-[var(--on-accent)] border border-transparent shadow-[var(--shadow-1)] hover:bg-[var(--accent-strong)] hover:text-[var(--on-accent)] active:brightness-95",
  secondary:
    "bg-[var(--surface)] text-[var(--ink)] border border-[var(--border-strong)] shadow-[var(--shadow-1)] hover:bg-[var(--subtle)] active:bg-[var(--pressed)]",
  ghost:
    "bg-transparent text-[var(--ink)] border border-transparent hover:bg-[var(--hover)] active:bg-[var(--pressed)]",
  danger:
    "bg-[var(--danger)] text-[var(--on-status)] border border-transparent shadow-[var(--shadow-1)] hover:brightness-110 active:brightness-95",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-[length:var(--text-small)] leading-5 gap-1.5 max-md:min-h-11",
  md: "px-4 py-2.5 text-[length:var(--text-body)] leading-5 gap-2 max-md:min-h-11",
};

export function buttonClassName(
  variant: ButtonVariant = "primary",
  size: ButtonSize = "md",
  className = "",
) {
  return `inline-flex items-center justify-center rounded-[var(--radius)] font-medium whitespace-nowrap transition-[background-color,border-color,filter,box-shadow] duration-150 ease-out motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none aria-busy:cursor-progress aria-busy:[--spinner:currentColor] ${variantClasses[variant]} ${sizeClasses[size]} ${className}`.trim();
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
      aria-busy={loading || undefined}
      className={buttonClassName(variant, size, className)}
      {...props}
    >
      {loading ? <Spinner size="sm" /> : null}
      {children}
    </button>
  );
}
