import Link from "next/link";
import { BookOpen, CalendarDays, GraduationCap, NotebookPen } from "lucide-react";
import type { ComponentType, ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { StatusChip } from "@/components/ui/status-chip";
import type { Day } from "@/lib/api/days";

const MOOD_WORDS: Record<string, string> = {
  great: "Great",
  good: "Good",
  okay: "Okay",
  low: "Low",
  bad: "Bad",
};

function timeOf(startsAt: string): string {
  if (!startsAt.includes("T")) return "All day";
  const d = new Date(startsAt);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function Row({
  icon: Icon,
  title,
  href,
  linkLabel,
  children,
}: {
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  title: string;
  href?: string;
  linkLabel?: string;
  children: ReactNode;
}) {
  return (
    <li className="flex gap-3 py-3 first:pt-0 last:pb-0">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
        <Icon className="h-4 w-4" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-[var(--ink)]">{title}</p>
          {href ? (
            <Link href={href} className="text-xs font-medium text-[var(--accent)] hover:underline">
              {linkLabel}
            </Link>
          ) : null}
        </div>
        <div className="mt-0.5 text-sm text-[var(--muted)]">{children}</div>
      </div>
    </li>
  );
}

/**
 * Everything else that belongs to the selected day: calendar, diary, reading and words.
 * Only blocks that have something to show appear, and the card is hidden when nothing does.
 */
export function DayJournalCard({ day }: { day: Day }) {
  const reading = day.readings
    .map((r) => (typeof r.reference === "string" ? r.reference : ""))
    .filter(Boolean);
  const reviewed = day.learned?.reviewed ?? 0;
  const hasAny = day.events.length > 0 || Boolean(day.diary) || reading.length > 0 || reviewed > 0;
  if (!hasAny) return null;

  return (
    <Card id="day-journal-title" title="Also on this day">
      <ul className="divide-y divide-[var(--border)]">
        {day.events.length > 0 ? (
          <Row icon={CalendarDays} title="Calendar" href="/calendar" linkLabel="Open calendar">
            <ul className="flex flex-col gap-0.5">
              {day.events.slice(0, 4).map((e) => (
                <li key={e.id}>
                  <span className="tabular-nums">{timeOf(e.startsAt)}</span> · {e.title}
                </li>
              ))}
              {day.events.length > 4 ? <li>and {day.events.length - 4} more</li> : null}
            </ul>
          </Row>
        ) : null}
        {day.diary ? (
          <Row icon={NotebookPen} title="Diary" href="/library?tab=diary" linkLabel="Open diary">
            <span className="flex items-start gap-2">
              {day.diary.mood ? (
                <StatusChip tone="accent">
                  {MOOD_WORDS[day.diary.mood] ?? day.diary.mood}
                </StatusChip>
              ) : null}
              <span className="line-clamp-2">{day.diary.body}</span>
            </span>
          </Row>
        ) : null}
        {reading.length > 0 ? (
          <Row icon={BookOpen} title="Reading" href="/learn?tab=reading" linkLabel="Open reading">
            {reading.join(", ")}
          </Row>
        ) : null}
        {reviewed > 0 ? (
          <Row icon={GraduationCap} title="Words" href="/learn" linkLabel="Open Learn">
            {reviewed} {reviewed === 1 ? "word" : "words"} reviewed
          </Row>
        ) : null}
      </ul>
    </Card>
  );
}
