"use client";

import { FormEvent, useEffect, useState } from "react";
import { Check, Repeat } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  archiveHabit,
  checkInHabit,
  createHabit,
  describeRule,
  getHabitGrid,
  listHabits,
  SCHEDULE_CHOICES,
  undoHabitCheckIn,
  type HabitGrid,
} from "@/lib/api/habits";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";

const DOT: Record<string, string> = {
  done: "bg-[var(--accent)]",
  skipped: "bg-[var(--border-strong)]",
  open: "border border-[var(--border-strong)]",
  off: "opacity-0",
};

function AddHabit({ onAdded }: { onAdded: () => void }) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [schedule, setSchedule] = useState("daily");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      const rule =
        SCHEDULE_CHOICES.find((s) => s.id === schedule)?.rule ?? SCHEDULE_CHOICES[0].rule;
      await createHabit({ name: name.trim(), rule });
      setName("");
      onAdded();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row" aria-label="Add a habit">
      <label htmlFor="habit-name" className="sr-only">
        New habit
      </label>
      <Input
        id="habit-name"
        value={name}
        maxLength={120}
        placeholder="New habit, e.g. Morning prayer"
        className="min-h-11 flex-1"
        onChange={(e) => setName(e.target.value)}
      />
      <label htmlFor="habit-schedule" className="sr-only">
        How often
      </label>
      <Select
        id="habit-schedule"
        value={schedule}
        className="min-h-11 sm:w-40"
        onChange={(e) => setSchedule(e.target.value)}
      >
        {SCHEDULE_CHOICES.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label}
          </option>
        ))}
      </Select>
      <Button type="submit" className="min-h-11" loading={saving} disabled={!name.trim()}>
        Add
      </Button>
    </form>
  );
}

/**
 * One list, one row per habit: tick today, see the last 7 days and the streak. Nothing is
 * repeated in a second card, and a tap changes the row at once without reloading the page.
 */
export function HabitsPage({ embedded = false }: { embedded?: boolean }) {
  void embedded;
  const { toast } = useToast();
  const grid = useLoad(() => getHabitGrid(7));
  const habits = useLoad(listHabits);
  const [view, setView] = useState<HabitGrid | null>(null);
  useEffect(() => setView(grid.data), [grid.data]);

  const streakOf = (id: string) => habits.data?.find((h) => h.id === id)?.streak ?? null;

  async function toggle(habitId: string, today: string, done: boolean) {
    const next = done ? "open" : "done";
    setView((prev) =>
      prev
        ? {
            ...prev,
            rows: prev.rows.map((r) =>
              r.habit.id === habitId
                ? { ...r, cells: r.cells.map((c) => (c.day === today ? { ...c, state: next } : c)) }
                : r,
            ),
          }
        : prev,
    );
    try {
      if (done) await undoHabitCheckIn(habitId, today);
      else await checkInHabit(habitId, { status: "done", day: today });
      void habits.reload();
    } catch (err) {
      setView(grid.data);
      toast(apiErrorMessage(err), "danger");
    }
  }

  async function remove(id: string, name: string) {
    try {
      await archiveHabit(id);
      toast(`${name} archived`);
      void grid.reload();
      void habits.reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  if (grid.error)
    return <ErrorBlock what="habits" message={grid.error} onRetry={() => void grid.reload()} />;
  if (!view) return <CardSkeleton rows={4} />;

  const today = view.to;
  const dueToday = view.rows.filter((r) => r.cells[r.cells.length - 1]?.state !== "off");
  const doneToday = dueToday.filter((r) => r.cells[r.cells.length - 1]?.state === "done").length;

  return (
    <div className="flex flex-col gap-5">
      <Card
        id="habits-list"
        title="Habits"
        description={
          dueToday.length > 0 ? `${doneToday} of ${dueToday.length} done today` : undefined
        }
      >
        {view.rows.length === 0 ? (
          <EmptyState
            compact
            icon={Repeat}
            title="No habits yet"
            description="Add one below, like morning prayer or exercise. It repeats on its own."
          />
        ) : (
          <ul className="flex flex-col divide-y divide-[var(--border)]">
            {view.rows.map((row) => {
              const last = row.cells[row.cells.length - 1];
              const due = last?.state !== "off";
              const done = last?.state === "done";
              const streak = streakOf(row.habit.id);
              return (
                <li
                  key={row.habit.id}
                  className="grid grid-cols-[2.75rem_minmax(0,1fr)_auto_auto] items-center gap-x-3 py-3 first:pt-0 last:pb-0"
                >
                  <button
                    type="button"
                    aria-pressed={done}
                    aria-label={`${row.habit.name}: ${done ? "done today, tap to undo" : "tap to mark done"}`}
                    disabled={!due}
                    onClick={() => void toggle(row.habit.id, today, done)}
                    className={`inline-flex h-11 w-11 items-center justify-center rounded-full border transition ${
                      done
                        ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--on-accent)]"
                        : "border-[var(--border-strong)] text-transparent hover:border-[var(--accent)]"
                    } disabled:opacity-40`}
                  >
                    <Check className="h-5 w-5" aria-hidden />
                  </button>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-[var(--ink)]">
                      {row.habit.name}
                    </p>
                    <p className="truncate text-xs text-[var(--muted)]">
                      {describeRule(row.habit.rule)}
                      {streak ? ` · streak ${streak.current} (best ${streak.best})` : ""}
                      {!due ? " · not due today" : ""}
                    </p>
                  </div>
                  <div
                    className="hidden items-center gap-1.5 sm:flex"
                    role="img"
                    aria-label={`${row.habit.name}, last 7 days`}
                  >
                    {row.cells.map((cell) => (
                      <span
                        key={cell.day}
                        title={`${cell.day}: ${cell.state}`}
                        className={`h-3.5 w-3.5 rounded-full ${DOT[cell.state]}`}
                      />
                    ))}
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label={`Archive ${row.habit.name}`}
                    onClick={() => void remove(row.habit.id, row.habit.name)}
                  >
                    Archive
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <AddHabit
        onAdded={() => {
          void grid.reload();
          void habits.reload();
        }}
      />
    </div>
  );
}
