"use client";

import { useState } from "react";
import { Check, Flame } from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { checkInHabit, undoHabitCheckIn, type HabitToday } from "@/lib/api/habits";

/**
 * One tappable chip per habit due today. Tap to check in, tap again to undo.
 * Used by Today and by the Habits tab so there is a single way to tick a habit.
 */
export function HabitChips({ data, onChange }: { data: HabitToday; onChange: () => void }) {
  const { toast } = useToast();
  const [busy, setBusy] = useState<string | null>(null);

  async function toggle(id: string, done: boolean) {
    setBusy(id);
    try {
      if (done) await undoHabitCheckIn(id, data.day);
      else await checkInHabit(id, { status: "done", day: data.day });
      onChange();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(null);
    }
  }

  return (
    <ul className="flex flex-wrap gap-2" aria-label="Habits due today">
      {data.items.map((habit) => {
        const done = habit.status === "done";
        const skipped = habit.status === "skipped";
        return (
          <li key={habit.id}>
            <button
              type="button"
              aria-pressed={done}
              disabled={busy === habit.id || skipped}
              onClick={() => void toggle(habit.id, done)}
              className={`inline-flex min-h-11 items-center gap-2 rounded-full border px-3.5 text-sm font-medium transition disabled:opacity-60 ${
                done
                  ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                  : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--canvas)]"
              }`}
            >
              <span
                aria-hidden
                className={`inline-flex h-5 w-5 items-center justify-center rounded-full border ${
                  done
                    ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--on-accent)]"
                    : "border-[var(--border-strong)]"
                }`}
              >
                {done ? <Check className="h-3 w-3" /> : null}
              </span>
              <span className={skipped ? "line-through" : ""}>{habit.name}</span>
              {habit.streak && habit.streak.current > 1 ? (
                <span className="inline-flex items-center gap-0.5 text-xs text-[var(--muted)]">
                  <Flame className="h-3 w-3" aria-hidden />
                  {habit.streak.current}
                </span>
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
