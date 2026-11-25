import type { TextareaHTMLAttributes } from "react";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

const base =
  "w-full min-h-[88px] resize-y py-2 leading-[var(--leading-body)] rounded-[var(--radius)] border border-[var(--border-strong)] bg-[var(--surface)] px-3 text-[length:var(--text-body)] text-[var(--ink)] placeholder:text-[var(--muted)] transition-[border-color,box-shadow] duration-150 motion-reduce:transition-none hover:border-[var(--muted)] focus:border-[var(--accent)] focus:outline-none focus:ring-[3px] focus:ring-[var(--ring)] disabled:cursor-not-allowed disabled:bg-[var(--subtle)] disabled:opacity-60 aria-[invalid=true]:border-[var(--danger)]";

export function Textarea({ className = "", ...props }: TextareaProps) {
  return <textarea className={`${base} ${className}`} {...props} />;
}
