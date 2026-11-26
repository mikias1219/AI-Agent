"use client";

import { FormEvent, useState } from "react";
import { Repeat } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  archiveHabit,
  createHabit,
  describeRule,
  getHabitGrid,
  getHabitsToday,
  listHabits,
  SCHEDULE_CHOICES,
} from "@/lib/api/habits";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";
import { HabitChips } from "./habit-chips";

const CELL: Record<string, string> = {
  done: "bg-[var(--accent)]",
  skipped: "bg-[var(--border-strong)]",
  open: "border border-[var(--border-strong)] bg-transparent",
  off: "bg-transparent opacity-30",
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
    <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <Field label="New habit" htmlFor="habit-name" className="flex-1">
        <Input
          id="habit-name"
          value={name}
          maxLength={120}
          placeholder="e.g. Morning prayer, Exercise, Read Bible"
          className="min-h-11"
          onChange={(e) => setName(e.target.value)}
        />
      </Field>
      <Field label="How often" htmlFor="habit-schedule">
        <Select
          id="habit-schedule"
          value={schedule}
          className="min-h-11"
          onChange={(e) => setSchedule(e.target.value)}
        >
          {SCHEDULE_CHOICES.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </Select>
      </Field>
      <Button type="submit" className="min-h-11" loading={saving} disabled={!name.trim()}>
        Add habit
      </Button>
    </form>
  );
}

export function HabitsPage({ embedded = false }: { embedded?: boolean }) {
  void embedded;
  const { toast } = useToast();
  const today = useLoad(getHabitsToday);
  const all = useLoad(listHabits);
  const grid = useLoad(() => getHabitGrid(7));

  const reload = () => {
    void today.reload();
    void all.reload();
    void grid.reload();
  };

  async function remove(id: string, name: string) {
    try {
      await archiveHabit(id);
      toast(`${name} archived`);
      reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  if (today.error) return <ErrorBlock what="habits" message={today.error} onRetry={reload} />;
  if (today.loading && !today.data) return <CardSkeleton rows={4} />;

  return (
    <div className="flex flex-col gap-5">
      <Card
        id="habits-today"
        title="Today"
        description={
          today.data && today.data.due > 0
            ? `${today.data.done} of ${today.data.due} done`
            : "Tick habits as you go."
        }
      >
        {today.data && today.data.items.length > 0 ? (
          <HabitChips data={today.data} onChange={reload} />
        ) : (
          <EmptyState
            compact
            icon={Repeat}
            title="No habits due today"
            description="Add a habit below, like morning prayer or exercise. It repeats on its own."
          />
        )}
      </Card>

      <Card id="habits-add" title="Add a habit">
        <AddHabit onAdded={reload} />
      </Card>

      {grid.data && grid.data.rows.length > 0 ? (
        <Card id="habits-grid" title="Last 7 days" description="Filled = done, grey = skipped.">
          <div className="flex flex-col gap-3 overflow-x-auto">
            {grid.data.rows.map((row) => (
              <div key={row.habit.id} className="flex items-center gap-3">
                <span className="w-40 shrink-0 truncate text-sm text-[var(--ink)]">
                  {row.habit.name}
                </span>
                <div
                  className="flex gap-1.5"
                  role="img"
                  aria-label={`${row.habit.name}, last 7 days`}
                >
                  {row.cells.map((cell) => (
                    <span
                      key={cell.day}
                      title={`${cell.day}: ${cell.state}`}
                      className={`h-5 w-5 rounded ${CELL[cell.state]}`}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {all.data && all.data.length > 0 ? (
        <Card id="habits-all" title="All habits">
          <ul className="flex flex-col divide-y divide-[var(--border)]">
            {all.data.map((habit) => (
              <li key={habit.id} className="flex flex-wrap items-center gap-3 py-3 first:pt-0">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-[var(--ink)]">{habit.name}</p>
                  <p className="text-xs text-[var(--muted)]">
                    {describeRule(habit.rule)}
                    {habit.streak
                      ? ` · streak ${habit.streak.current} (best ${habit.streak.best}) · ${habit.streak.done_last_30}/${habit.streak.due_last_30} in 30 days`
                      : ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Archive ${habit.name}`}
                  onClick={() => void remove(habit.id, habit.name)}
                >
                  Archive
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
