import type { ReactNode } from "react";

export type CompactRowProps = {
  title: string;
  meta?: string;
  chip?: ReactNode;
  onClick?: () => void;
};

export function CompactRow({ title, meta, chip, onClick }: CompactRowProps) {
  const rowClassName =
    "flex w-full items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 text-left transition";
  const sizeClass = "min-h-[var(--row-min-h)] py-[var(--row-pad-y)]";

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
        className={`${rowClassName} ${sizeClass} cursor-pointer hover:bg-[var(--canvas)]`}
      >
        {content}
      </button>
    );
  }

  return <div className={`${rowClassName} ${sizeClass}`}>{content}</div>;
}
