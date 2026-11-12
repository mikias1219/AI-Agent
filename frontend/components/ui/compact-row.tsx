import type { ReactNode } from "react";

export type CompactRowProps = {
  title: string;
  meta?: string;
  chip?: ReactNode;
  onClick?: () => void;
};

export function CompactRow({ title, meta, chip, onClick }: CompactRowProps) {
  const rowClassName =
    "flex w-full min-h-11 items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5 text-left transition";

  const content = (
    <>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-[var(--ink)]">{title}</p>
        {meta ? <p className="truncate text-xs text-[var(--muted)]">{meta}</p> : null}
      </div>
      {chip ? <div className="shrink-0">{chip}</div> : null}
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`${rowClassName} cursor-pointer hover:bg-[var(--canvas)]`}
      >
        {content}
      </button>
    );
  }

  return <div className={rowClassName}>{content}</div>;
}
