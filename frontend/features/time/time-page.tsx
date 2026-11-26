"use client";

import { FormEvent, useEffect, useState } from "react";
import { Play, Square, Timer, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { IconButton } from "@/components/ui/icon-button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { listTasks } from "@/lib/api/tasks";
import {
  deleteTimeEntry,
  formatMinutes,
  getRunningTimer,
  getTimeSummary,
  listTimeEntries,
  logTime,
  startTimer,
  stopTimer,
} from "@/lib/api/time";
import { formatDate } from "@/lib/format-date";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";

function elapsed(startedAt: string, now: number): string {
  const secs = Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000));
  const h = String(Math.floor(secs / 3600)).padStart(2, "0");
  const m = String(Math.floor((secs % 3600) / 60)).padStart(2, "0");
  const s = String(secs % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

/** Start, stop and log time; see where the week went. One running timer at a time. */
export function TimePage({ embedded = false }: { embedded?: boolean }) {
  void embedded;
  const { toast } = useToast();
  const running = useLoad(getRunningTimer);
  const summary = useLoad(() => getTimeSummary());
  const entries = useLoad(() => listTimeEntries());
  const tasks = useLoad(() => listTasks());
  const [taskId, setTaskId] = useState("");
  const [project, setProject] = useState("");
  const [minutes, setMinutes] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);

  const current = running.data?.entry ?? null;
  useEffect(() => {
    if (!current) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [current]);

  const reload = () => {
    void running.reload();
    void summary.reload();
    void entries.reload();
  };
  const openTasks = (tasks.data ?? []).filter(
    (t) => t.status !== "done" && t.status !== "cancelled",
  );
  const titleOf = (id: string | null) => tasks.data?.find((t) => t.id === id)?.title;

  async function run(action: () => Promise<unknown>, done?: string) {
    setBusy(true);
    try {
      await action();
      if (done) toast(done);
      reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  function onManual(event: FormEvent) {
    event.preventDefault();
    const value = Number(minutes);
    if (!Number.isInteger(value) || value < 1) return;
    void run(
      () =>
        logTime({
          minutes: value,
          ...(taskId ? { task_id: taskId } : {}),
          ...(project.trim() ? { project: project.trim() } : {}),
        }),
      "Time logged",
    ).then(() => setMinutes(""));
  }

  if (running.error) return <ErrorBlock what="time" message={running.error} onRetry={reload} />;
  if (running.loading && !running.data) return <CardSkeleton rows={4} />;

  const link = {
    ...(taskId ? { task_id: taskId } : {}),
    ...(project.trim() ? { project: project.trim() } : {}),
  };
  const maxDay = Math.max(1, ...Object.values(summary.data?.by_day ?? {}));

  return (
    <div className="flex flex-col gap-5">
      <Card id="time-timer" title="Timer" description="One timer runs at a time.">
        {current ? (
          <div className="flex flex-wrap items-center gap-4">
            <p
              className="text-3xl font-semibold tabular-nums text-[var(--ink)]"
              role="timer"
              aria-live="off"
            >
              {elapsed(current.started_at, now)}
            </p>
            <p className="min-w-0 flex-1 truncate text-sm text-[var(--muted)]">
              {titleOf(current.task_id) ?? (current.project || "No task")}
            </p>
            <Button
              variant="danger"
              className="min-h-11"
              loading={busy}
              onClick={() => void run(stopTimer, "Timer stopped")}
            >
              <Square className="h-4 w-4" aria-hidden />
              Stop
            </Button>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <Field label="Task (optional)" htmlFor="time-task">
              <Select
                id="time-task"
                className="min-h-11"
                value={taskId}
                onChange={(e) => setTaskId(e.target.value)}
              >
                <option value="">No task</option>
                {openTasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Project (optional)" htmlFor="time-project">
              <Input
                id="time-project"
                className="min-h-11"
                value={project}
                placeholder="e.g. Learning"
                onChange={(e) => setProject(e.target.value)}
              />
            </Field>
            <Button
              className="min-h-11"
              loading={busy}
              onClick={() => void run(() => startTimer(link), "Timer started")}
            >
              <Play className="h-4 w-4" aria-hidden />
              Start
            </Button>
          </div>
        )}
      </Card>

      <Card id="time-manual" title="Log time you already spent">
        <form onSubmit={onManual} className="flex flex-wrap items-end gap-3">
          <Field label="Minutes" htmlFor="time-minutes">
            <Input
              id="time-minutes"
              inputMode="numeric"
              className="min-h-11 w-28"
              value={minutes}
              placeholder="35"
              onChange={(e) => setMinutes(e.target.value.replace(/\D/g, ""))}
            />
          </Field>
          <p className="pb-3 text-xs text-[var(--muted)]">
            Uses the task and project chosen above, for today.
          </p>
          <Button
            type="submit"
            variant="secondary"
            className="min-h-11"
            disabled={!minutes || busy}
          >
            Log time
          </Button>
        </form>
      </Card>

      <Card
        id="time-summary"
        title="Last 7 days"
        description={
          summary.data ? `${formatMinutes(summary.data.total_minutes)} tracked` : undefined
        }
      >
        {summary.data && summary.data.total_minutes > 0 ? (
          <div className="grid gap-6 md:grid-cols-2">
            <ul className="flex flex-col gap-2" aria-label="By project">
              {summary.data.by_project.map((row) => (
                <li key={row.project} className="flex flex-col gap-1">
                  <div className="flex justify-between text-sm">
                    <span className="truncate text-[var(--ink)]">{row.project}</span>
                    <span className="text-xs text-[var(--muted)] tabular-nums">
                      {formatMinutes(row.minutes)}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-[var(--subtle)]">
                    <div
                      className="h-full rounded-full bg-[var(--accent)]"
                      style={{ width: `${(row.minutes / summary.data!.total_minutes) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
            <ul className="flex flex-col gap-1.5" aria-label="By day">
              {Object.entries(summary.data.by_day).map(([day, mins]) => (
                <li
                  key={day}
                  className="grid grid-cols-[5.5rem_1fr_4rem] items-center gap-2 text-xs"
                >
                  <span className="text-[var(--muted)]">{formatDate(day)}</span>
                  <div
                    className="h-2 rounded-full bg-[var(--chart-2)]"
                    style={{ width: `${(mins / maxDay) * 100}%` }}
                  />
                  <span className="text-right tabular-nums text-[var(--muted)]">
                    {formatMinutes(mins)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <EmptyState
            compact
            icon={Timer}
            title="No time tracked yet"
            description="Start the timer on a task, or log time you already spent."
          />
        )}
      </Card>

      {entries.data && entries.data.length > 0 ? (
        <Card id="time-entries" title="Entries">
          <ul className="flex flex-col divide-y divide-[var(--border)]">
            {entries.data.slice(0, 15).map((e) => (
              <li
                key={e.id}
                className="flex items-center gap-3 py-2.5 text-sm first:pt-0 last:pb-0"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[var(--ink)]">
                    {titleOf(e.task_id) ?? (e.project || "No task")}
                  </p>
                  <p className="text-xs text-[var(--muted)]">
                    {formatDate(e.started_at)} · {e.source === "manual" ? "logged" : "timer"}
                    {e.running ? " · running" : ""}
                  </p>
                </div>
                <span className="tabular-nums text-[var(--muted)]">{formatMinutes(e.minutes)}</span>
                {!e.running ? (
                  <IconButton
                    label="Delete entry"
                    onClick={() => void run(() => deleteTimeEntry(e.id), "Entry deleted")}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </IconButton>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
