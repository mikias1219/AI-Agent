import type { HTMLAttributes } from "react";

export type AvatarProps = HTMLAttributes<HTMLDivElement> & {
  name?: string;
  src?: string;
  size?: "sm" | "md" | "lg";
};

const sizeClasses = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
};

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Avatar({
  name = "",
  src,
  size = "md",
  className = "",
  ...props
}: AvatarProps) {
  return (
    <div
      className={`inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-[var(--border)] bg-[var(--accent-soft)] font-medium text-[var(--accent)] ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={name || "Avatar"} className="h-full w-full object-cover" />
      ) : (
        <span aria-hidden>{initials(name || "?")}</span>
      )}
    </div>
  );
}
