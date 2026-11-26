"use client";

import { FormEvent, useEffect, useState } from "react";
import { Play, Square, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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

  return (
    <div className="flex flex-col gap-5">
      <Card id="time-timer" title="Time">
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
          <form onSubmit={onManual} className="flex flex-col gap-4">
            <div className="grid gap-3 sm:grid-cols-2">
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
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                className="min-h-11"
                loading={busy}
                onClick={() => void run(() => startTimer(link), "Timer started")}
              >
                <Play className="h-4 w-4" aria-hidden />
                Start timer
              </Button>
              <span className="text-sm text-[var(--muted)]">or log minutes spent today</span>
              <label htmlFor="time-minutes" className="sr-only">
                Minutes
              </label>
              <Input
                id="time-minutes"
                inputMode="numeric"
                className="min-h-11 w-24"
                value={minutes}
                placeholder="35"
                onChange={(e) => setMinutes(e.target.value.replace(/\D/g, ""))}
              />
              <Button
                type="submit"
                variant="secondary"
                className="min-h-11"
                disabled={!minutes || busy}
              >
                Log
              </Button>
            </div>
          </form>
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
