"use client";

import { useRef, type KeyboardEvent } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Input } from "@/components/ui/input";
import type { DayRangeRow } from "@/lib/api/days";
import {
  addDays,
  canStep,
  chipLabel,
  clampDay,
  dayHeading,
  scorePercent,
  weekDates,
} from "./day-logic";

export type DaySwitcherProps = {
  date: string;
  today: string;
  onChange: (date: string) => void;
};

export function DaySwitcher({ date, today, onChange }: DaySwitcherProps) {
  const heading = dayHeading(date);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="text-lg font-semibold text-[var(--ink)]" aria-live="polite">
          {heading.weekday}
          {date === today ? " (today)" : ""}
        </p>
        <p className="text-sm text-[var(--muted)]">{heading.full}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <IconButton
          label="Previous day"
          className="!h-11 !w-11"
          disabled={!canStep(date, -1, today)}
          onClick={() => onChange(addDays(date, -1))}
        >
          <ChevronLeft size={18} aria-hidden />
        </IconButton>
        <Button
          variant="secondary"
          className="min-h-11"
          disabled={date === today}
          onClick={() => onChange(today)}
        >
          Today
        </Button>
        <IconButton
          label="Next day"
          className="!h-11 !w-11"
          disabled={!canStep(date, 1, today)}
          onClick={() => onChange(addDays(date, 1))}
        >
          <ChevronRight size={18} aria-hidden />
        </IconButton>
        <Input
          type="date"
          aria-label="Pick a day"
          value={date}
          onChange={(event) => {
            if (event.target.value) onChange(clampDay(event.target.value, today));
          }}
          className="min-h-11 !w-40 shrink-0"
        />
      </div>
    </div>
  );
}

function dotClass(score: number | null): string {
  if (score === null) return "bg-[var(--border)]";
  if (score >= 0.8) return "bg-[var(--success)]";
  if (score >= 0.5) return "bg-[var(--warning)]";
  return "bg-[var(--danger)]";
}

export type WeekStripProps = {
  date: string;
  today: string;
  rows: DayRangeRow[];
  onChange: (date: string) => void;
};

export function WeekStrip({ date, today, rows, onChange }: WeekStripProps) {
  const days = weekDates(date);
  const byDate = new Map(rows.map((row) => [row.date, row]));
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = days.indexOf(date);
    let next = index;
    if (event.key === "ArrowRight") next = index + 1;
    else if (event.key === "ArrowLeft") next = index - 1;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = days.length - 1;
    else return;
    event.preventDefault();
    // Moving past either end steps into the neighbouring week.
    const target = next < 0 ? addDays(days[0], -1) : next > 6 ? addDays(days[6], 1) : days[next];
    const clamped = clampDay(target, today);
    onChange(clamped);
    window.setTimeout(() => refs.current[clamped]?.focus(), 0);
  }

  return (
    <div
      role="group"
      aria-label="This week"
      onKeyDown={onKeyDown}
      className="grid grid-cols-7 gap-1.5"
    >
      {days.map((key) => {
        const label = chipLabel(key);
        const row = byDate.get(key);
        const pct = row ? scorePercent(row.score) : null;
        const selected = key === date;
        const description = row
          ? pct !== null
            ? `${row.planned} tasks, score ${pct}%`
            : `${row.planned} tasks`
          : "no tasks";
        return (
          <button
            key={key}
            type="button"
            ref={(el) => {
              refs.current[key] = el;
            }}
            aria-pressed={selected}
            aria-label={`${label.weekday} ${label.day}, ${description}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(key)}
            className={`flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-[var(--radius)] border px-1 py-1.5 text-center transition focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${
              selected
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--canvas)]"
            }`}
          >
            <span className="text-[length:var(--text-caption)] text-[var(--muted)]">
              {label.weekday}
            </span>
            <span className={`text-sm font-semibold ${key === today ? "underline" : ""}`}>
              {label.day}
            </span>
            <span
              aria-hidden
              className={`h-1.5 w-1.5 rounded-full ${row ? dotClass(row.score) : "bg-transparent"}`}
            />
          </button>
        );
      })}
    </div>
  );
}
