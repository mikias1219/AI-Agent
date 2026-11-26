"use client";

import { useState } from "react";

export type BarSeries = { key: string; label: string; color: string };
export type BarDatum = { label: string; counts: Record<string, number> };

export type StackedBarChartProps = {
  data: BarDatum[];
  series: BarSeries[];
  /** Short description for assistive tech, e.g. "Compass activity per day, last 7 days". */
  label: string;
  height?: number;
};

const W = 560;
const PAD = { top: 12, right: 8, bottom: 24, left: 28 };

function niceMax(value: number): number {
  if (value <= 4) return 4;
  const pow = 10 ** Math.floor(Math.log10(value));
  const n = value / pow;
  return (n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;
}

/** Stacked columns per day with gridlines, hover tooltip and a legend. Series colour is never the only cue: a data table follows for screen readers. */
export function StackedBarChart({ data, series, label, height = 200 }: StackedBarChartProps) {
  const [active, setActive] = useState<number | null>(null);
  const totals = data.map((d) => series.reduce((n, s) => n + (d.counts[s.key] ?? 0), 0));
  const top = niceMax(Math.max(...totals, 0));
  const innerW = W - PAD.left - PAD.right;
  const innerH = height - PAD.top - PAD.bottom;
  const slot = innerW / Math.max(data.length, 1);
  const barW = Math.min(36, slot * 0.6);
  const ticks = [0, top / 2, top];

  const tip = active !== null ? data[active] : null;

  return (
    <figure className="m-0">
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label={label} className="h-auto w-full">
          {ticks.map((t) => {
            const y = PAD.top + innerH - (t / top) * innerH;
            return (
              <g key={t}>
                <line
                  x1={PAD.left}
                  x2={W - PAD.right}
                  y1={y}
                  y2={y}
                  stroke="var(--border)"
                  strokeWidth={1}
                />
                <text x={PAD.left - 6} y={y + 3} textAnchor="end" fontSize={10} fill="var(--muted)">
                  {Math.round(t)}
                </text>
              </g>
            );
          })}
          {data.map((d, i) => {
            const x = PAD.left + i * slot + (slot - barW) / 2;
            let y = PAD.top + innerH;
            return (
              <g
                key={`${d.label}-${i}`}
                onMouseEnter={() => setActive(i)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(i)}
                onBlur={() => setActive(null)}
                tabIndex={0}
                aria-label={`${d.label}: ${totals[i]} events`}
              >
                <rect
                  x={PAD.left + i * slot}
                  y={PAD.top}
                  width={slot}
                  height={innerH}
                  fill="transparent"
                />
                {series.map((s) => {
                  const v = d.counts[s.key] ?? 0;
                  if (v <= 0) return null;
                  const h = (v / top) * innerH;
                  y -= h;
                  return (
                    <rect
                      key={s.key}
                      x={x}
                      y={y}
                      width={barW}
                      height={Math.max(h - 1, 1)}
                      rx={2}
                      fill={s.color}
                      opacity={active === null || active === i ? 1 : 0.45}
                    />
                  );
                })}
                <text
                  x={PAD.left + i * slot + slot / 2}
                  y={height - 6}
                  textAnchor="middle"
                  fontSize={10}
                  fill="var(--muted)"
                >
                  {d.label}
                </text>
              </g>
            );
          })}
        </svg>
        {tip && active !== null ? (
          <div
            role="status"
            className="pointer-events-none absolute top-0 right-0 min-w-36 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs shadow-[var(--shadow-2)]"
          >
            <p className="font-semibold text-[var(--ink)]">
              {tip.label} · {totals[active]}
            </p>
            <ul className="mt-1 space-y-0.5">
              {series
                .filter((s) => (tip.counts[s.key] ?? 0) > 0)
                .map((s) => (
                  <li key={s.key} className="flex items-center gap-1.5 text-[var(--muted)]">
                    <span
                      aria-hidden
                      className="h-2 w-2 rounded-sm"
                      style={{ background: s.color }}
                    />
                    {s.label}: {tip.counts[s.key]}
                  </li>
                ))}
            </ul>
          </div>
        ) : null}
      </div>
      <figcaption className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--muted)]">
        {series.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <span aria-hidden className="h-2 w-2 rounded-sm" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
      </figcaption>
      <table className="sr-only">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th>Day</th>
            {series.map((s) => (
              <th key={s.key}>{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((d, i) => (
            <tr key={`${d.label}-${i}`}>
              <td>{d.label}</td>
              {series.map((s) => (
                <td key={s.key}>{d.counts[s.key] ?? 0}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
