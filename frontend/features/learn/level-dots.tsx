import { levelText } from "./learn-logic";

export function LevelDots({ box }: { box: number }) {
  const level = Math.min(5, Math.max(0, Math.round(box)));
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <span className="inline-flex gap-1" aria-hidden>
        {Array.from({ length: 5 }, (_, i) => (
          <span
            key={i}
            className={`h-2 w-2 rounded-full ${i < level ? "bg-[var(--accent)]" : "bg-[var(--border)]"}`}
          />
        ))}
      </span>
      <span className="text-[length:var(--text-caption)] text-[var(--muted)]">
        {levelText(box)}
      </span>
    </span>
  );
}
