import type { ReactNode } from "react";

export type CardProps = {
  id?: string;
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  /** Remove body padding so tables can run edge to edge. */
  flush?: boolean;
  className?: string;
};

/** The one container for dashboard blocks: title row, optional action, body. */
export function Card({
  id,
  title,
  description,
  action,
  children,
  flush,
  className = "",
}: CardProps) {
  return (
    <section
      aria-labelledby={title && id ? id : undefined}
      className={`flex min-w-0 flex-col rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-1)] ${className}`.trim()}
    >
      {title ? (
        <header className="flex items-start justify-between gap-3 px-[var(--card-pad)] pt-4 pb-3">
          <div className="min-w-0">
            <h2
              id={id}
              className="text-[length:var(--text-body)] leading-[var(--leading-title)] font-semibold tracking-[-0.005em] text-[var(--ink)]"
            >
              {title}
            </h2>
            {description ? (
              <p className="mt-0.5 text-[length:var(--text-small)] leading-5 text-[var(--muted)]">
                {description}
              </p>
            ) : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </header>
      ) : null}
      <div className={flush ? "" : `px-[var(--card-pad)] pb-4 ${title ? "" : "pt-4"}`.trim()}>
        {children}
      </div>
    </section>
  );
}
