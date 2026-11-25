import type { ButtonHTMLAttributes, ReactNode } from "react";

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  children: ReactNode;
  size?: "sm" | "md";
};

const sizeClasses = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
};

export function IconButton({
  label,
  children,
  size = "md",
  className = "",
  type = "button",
  ...props
}: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={`inline-flex items-center justify-center rounded-[var(--radius)] border border-transparent bg-transparent text-[var(--muted)] transition-colors duration-150 hover:bg-[var(--hover)] hover:text-[var(--ink)] active:bg-[var(--pressed)] motion-reduce:transition-none focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
