export type SparklineProps = {
  values: number[];
  /** Text alternative, e.g. "Runs per day, last 7 days: 0, 2, 5". */
  label: string;
  color?: string;
  width?: number;
  height?: number;
};

/** Tiny trend line for KPI cards. Renders nothing meaningful for fewer than two points. */
export function Sparkline({
  values,
  label,
  color = "var(--chart-1)",
  width = 96,
  height = 28,
}: SparklineProps) {
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const pad = 2;
  const step = (width - pad * 2) / (values.length - 1);
  const points = values.map(
    (v, i) => [pad + i * step, height - pad - (v / max) * (height - pad * 2)] as const,
  );
  const line = points
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");
  const area = `${line} L${points[points.length - 1]![0].toFixed(1)} ${height} L${points[0]![0].toFixed(1)} ${height} Z`;
  return (
    <svg
      role="img"
      aria-label={label}
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className="shrink-0"
    >
      <path d={area} fill={color} opacity={0.12} />
      <path
        d={line}
        fill="none"
        stroke={color}
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
