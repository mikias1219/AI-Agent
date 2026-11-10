import type { ReactNode } from "react";

export type FieldProps = {
  label: string;
  error?: string;
  children: ReactNode;
  className?: string;
};

export function Field({ label, error, children, className = "" }: FieldProps) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label className="text-sm font-medium text-[var(--ink)]">{label}</label>
      {children}
      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
