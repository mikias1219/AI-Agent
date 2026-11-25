export type DonutSlice = { key: string; label: string; value: number; color: string };

export type DonutChartProps = {
  slices: DonutSlice[];
  label: string;
  centerLabel?: string;
  size?: number;
};

/** Share-of-total ring with a legend that always shows the number, so colour is never the only cue. */
export function DonutChart({ slices, label, centerLabel = "total", size = 132 }: DonutChartProps) {
  const total = slices.reduce((n, s) => n + s.value, 0);
  const r = 46;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <figure className="m-0 flex flex-wrap items-center gap-5">
      <svg
        viewBox="0 0 120 120"
        width={size}
        height={size}
        role="img"
        aria-label={label}
        className="shrink-0"
      >
        <circle cx={60} cy={60} r={r} fill="none" stroke="var(--subtle)" strokeWidth={14} />
        {total > 0
          ? slices.map((s) => {
              const len = (s.value / total) * c;
              const el = (
                <circle
                  key={s.key}
                  cx={60}
                  cy={60}
                  r={r}
                  fill="none"
                  stroke={s.color}
                  strokeWidth={14}
                  strokeDasharray={`${Math.max(len - 1.5, 0)} ${c}`}
                  strokeDashoffset={-offset}
                  transform="rotate(-90 60 60)"
                />
              );
              offset += len;
              return el;
            })
          : null}
        <text x={60} y={58} textAnchor="middle" fontSize={20} fontWeight={600} fill="var(--ink)">
          {total}
        </text>
        <text x={60} y={74} textAnchor="middle" fontSize={9} fill="var(--muted)">
          {centerLabel}
        </text>
      </svg>
      <figcaption className="min-w-0 flex-1">
        <ul className="space-y-1.5 text-sm">
          {slices.map((s) => (
            <li key={s.key} className="flex items-center gap-2">
              <span
                aria-hidden
                className="h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ background: s.color }}
              />
              <span className="min-w-0 flex-1 truncate text-[var(--ink)]">{s.label}</span>
              <span className="tabular-nums text-[var(--muted)]">
                {s.value}
                {total > 0 ? ` · ${Math.round((s.value / total) * 100)}%` : ""}
              </span>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
