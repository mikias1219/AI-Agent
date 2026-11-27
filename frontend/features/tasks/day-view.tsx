"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { IconButton } from "@/components/ui/icon-button";
import { Input } from "@/components/ui/input";
import { Skeleton, SkeletonRows } from "@/components/ui/skeleton";
import { StatusChip, type StatusChipTone } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  carryOver,
  getDay,
  getDayRange,
  getDayStats,
  type Day,
  type DayRangeRow,
  type DayStats,
} from "@/lib/api/days";
import { driveSync, type DriveSyncStatus } from "@/lib/api/sync";
import { createTask, patchTask, type LifeTask, type TaskOutcome } from "@/lib/api/tasks";
import { DayJournalCard } from "./day-journal";
import { DaySwitcher, WeekStrip } from "./day-parts";
import {
  addDays,
  dayHeading,
  isOpen,
  outcomeText,
  scorePercent,
  summaryLine,
  targetText,
  toDateKey,
  weekRange,
} from "./day-logic";
import { OutcomePanel } from "./outcome-panel";
import { TaskDetailDrawer } from "./task-detail-drawer";

const OUTCOME_TONE: Record<TaskOutcome, StatusChipTone> = {
  achieved: "success",
  partial: "accent",
  missed: "danger",
  skipped: "neutral",
};

function formatTime(iso: string | null): string {
  if (!iso) return "";
  const due = new Date(iso);
  if (Number.isNaN(due.getTime())) return "";
  // Midnight and exactly 9:00 are "date only" defaults, not a chosen time: show nothing.
  const hm = due.getHours() * 60 + due.getMinutes();
  if (hm === 0 || (hm === 540 && due.getSeconds() === 0)) return "";
  return new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(due);
}

export function DayView() {
  const { toast } = useToast();
  const [today, setToday] = useState(() => toDateKey(new Date()));
  const [date, setDate] = useState(today);
  const [day, setDay] = useState<Day | null>(null);
  const [range, setRange] = useState<DayRangeRow[]>([]);
  const [stats, setStats] = useState<DayStats | null>(null);
  const [drive, setDrive] = useState<DriveSyncStatus | null>(null);
  const [driveUrl, setDriveUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completing, setCompleting] = useState<string | null>(null);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [detail, setDetail] = useState<LifeTask | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const requestRef = useRef(0);

  const week = weekRange(date);

  const load = useCallback(
    async (options?: { initial?: boolean }) => {
      const request = ++requestRef.current;
      if (options?.initial) setLoading(true);
      setError(null);
      try {
        const nextDay = await getDay(date);
        if (request !== requestRef.current) return;
        setDay(nextDay);
        setLoading(false);
        // Secondary data never blocks the list.
        const [rangeRows, nextStats, driveStatus] = await Promise.all([
          getDayRange(week.from, week.to).catch(() => null),
          getDayStats().catch(() => null),
          driveSync.status().catch(() => null),
        ]);
        if (request !== requestRef.current) return;
        setRange(rangeRows ?? []);
        setStats(nextStats);
        setDrive(driveStatus);
        let url = nextDay.drive_url ?? null;
        if (!url && driveStatus?.enabled && driveStatus.scope_granted) {
          const items = await driveSync.items({ object_type: "daily" }).catch(() => []);
          url = items.find((item) => item.object_id === date)?.drive_url ?? null;
        }
        if (request !== requestRef.current) return;
        setDriveUrl(url);
      } catch (err) {
        if (request !== requestRef.current) return;
        setError(apiErrorMessage(err));
        setLoading(false);
      }
    },
    [date, week.from, week.to],
  );

  useEffect(() => {
    void load({ initial: true });
  }, [load]);

  useEffect(() => {
    setCompleting(null);
    setMenuFor(null);
    setActionError(null);
  }, [date]);

  // Roll over if the page stays open past midnight.
  useEffect(() => {
    const id = window.setInterval(() => {
      const now = toDateKey(new Date());
      setToday((prev) => (prev === now ? prev : now));
    }, 60_000);
    return () => window.clearInterval(id);
  }, []);

  async function reopen(task: LifeTask) {
    setActionError(null);
    setBusyId(task.id);
    setMenuFor(null);
    // One tap on a finished task reopens it; keep the old result so Undo can restore it.
    const previous = task.outcome ?? "achieved";
    try {
      await patchTask(task.id, { status: "planned" });
      await load();
      toast(`Reopened “${task.title}”.`, {
        tone: "success",
        action: {
          label: "Undo",
          onClick: async () => {
            try {
              await patchTask(task.id, { outcome: previous });
              await load();
            } catch (err) {
              toast(apiErrorMessage(err), "danger");
            }
          },
        },
      });
    } catch (err) {
      setActionError(apiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  const summary = day?.summary;
  const tasks = day?.tasks ?? [];
  const pct = scorePercent(summary?.score);

  return (
    <div className="flex flex-col gap-4">
      <DaySwitcher date={date} today={today} onChange={setDate} />
      <WeekStrip date={date} today={today} rows={range} onChange={setDate} />

      {loading ? (
        <div className="flex flex-col gap-4" aria-busy="true">
          <Skeleton heightClass="h-10" className="w-full" />
          <SkeletonRows count={3} />
        </div>
      ) : null}

      {!loading && error ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
          <Button variant="secondary" size="sm" onClick={() => void load({ initial: true })}>
            Try again
          </Button>
        </div>
      ) : null}

      {!loading && !error && day && summary ? (
        <>
          <div className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-[var(--ink)]">
                {summaryLine(summary.done, summary.planned, summary.score)}
              </p>
              <div className="flex flex-wrap gap-2">
                {stats ? (
                  <>
                    <StatusChip tone={stats.streak_days > 0 ? "success" : "neutral"}>
                      {stats.streak_days === 1
                        ? "Streak: 1 day"
                        : `Streak: ${stats.streak_days} days`}
                    </StatusChip>
                    <StatusChip>
                      {stats.week.rate === null
                        ? "This week: no score yet"
                        : `This week: ${scorePercent(stats.week.rate)}%`}
                    </StatusChip>
                  </>
                ) : null}
              </div>
            </div>
            <div
              role="progressbar"
              aria-label="Day progress"
              aria-valuemin={0}
              aria-valuemax={Math.max(summary.planned, 1)}
              aria-valuenow={summary.done}
              aria-valuetext={summaryLine(summary.done, summary.planned, summary.score)}
              className="h-2 w-full overflow-hidden rounded-full bg-[var(--canvas)]"
            >
              <div
                className="h-full rounded-full bg-[var(--accent)] transition-[width]"
                style={{
                  width: `${summary.planned > 0 ? Math.round((summary.done / summary.planned) * 100) : 0}%`,
                }}
              />
            </div>
          </div>

          <QuickAdd
            date={date}
            onCreated={async () => {
              await load();
            }}
          />

          {actionError ? (
            <p className="text-sm text-[var(--danger)]" role="alert">
              {actionError}
            </p>
          ) : null}

          {tasks.length === 0 ? (
            <EmptyState
              title="Nothing planned for this day"
              description="Add a task above and it will be saved to this day."
              compact
            />
          ) : (
            <ul className="flex flex-col gap-2" aria-label="Tasks for this day">
              {tasks.map((task) => (
                <li
                  key={task.id}
                  className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3"
                >
                  <TaskRow
                    task={task}
                    busy={busyId === task.id}
                    menuOpen={menuFor === task.id}
                    onToggle={() => {
                      setMenuFor(null);
                      if (isOpen(task)) {
                        setCompleting((prev) => (prev === task.id ? null : task.id));
                      } else {
                        void reopen(task);
                      }
                    }}
                    onMenu={() => setMenuFor((prev) => (prev === task.id ? null : task.id))}
                    onOpen={() => setDetail(task)}
                    onReopen={() => void reopen(task)}
                    onEditOutcome={() => {
                      setMenuFor(null);
                      setCompleting(task.id);
                    }}
                  />
                  {completing === task.id ? (
                    <OutcomePanel
                      task={task}
                      onCancel={() => setCompleting(null)}
                      onSaved={() => {
                        setCompleting(null);
                        void load();
                      }}
                    />
                  ) : null}
                </li>
              ))}
            </ul>
          )}

          <DayJournalCard day={day} />

          <DaySummaryCard
            date={date}
            day={day}
            drive={drive}
            driveUrl={driveUrl}
            pct={pct}
            onCarried={async (moved, to) => {
              const when = dayHeading(to);
              toast(
                `Moved ${moved} ${moved === 1 ? "task" : "tasks"} to ${when.weekday}.`,
                "success",
              );
              await load();
            }}
          />
        </>
      ) : null}

      <TaskDetailDrawer
        task={detail}
        onClose={() => setDetail(null)}
        onSaved={(updated) => {
          setDetail(updated);
          void load();
        }}
      />
    </div>
  );
}

type TaskRowProps = {
  task: LifeTask;
  busy: boolean;
  menuOpen: boolean;
  onToggle: () => void;
  onMenu: () => void;
  onOpen: () => void;
  onReopen: () => void;
  onEditOutcome: () => void;
};

function TaskRow({
  task,
  busy,
  menuOpen,
  onToggle,
  onMenu,
  onOpen,
  onReopen,
  onEditOutcome,
}: TaskRowProps) {
  const finished = task.status === "done" || task.status === "cancelled";
  const time = formatTime(task.due_at);
  const target = targetText(task);
  const outcome = outcomeText(task);
  return (
    <div className="flex items-start gap-3">
      <button
        type="button"
        role="checkbox"
        aria-checked={task.status === "done"}
        aria-label={finished ? `Reopen ${task.title}` : `Mark ${task.title} as done`}
        disabled={busy}
        onClick={onToggle}
        className={`mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--radius)] border-2 transition focus-visible:outline-2 focus-visible:outline-[var(--accent)] disabled:opacity-50 ${
          task.status === "done"
            ? "border-[var(--success)] bg-[var(--success)] text-[var(--on-status)]"
            : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)]"
        }`}
      >
        {task.status === "done" ? (
          <svg viewBox="0 0 20 20" width="20" height="20" aria-hidden fill="none">
            <path
              d="M4 10.5l4 4 8-9"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        ) : null}
      </button>
      <div className="min-w-0 flex-1">
        <button
          type="button"
          aria-label={`Open ${task.title}`}
          onClick={onOpen}
          className="block min-h-11 w-full min-w-0 text-left"
        >
          <span
            className={`block break-words font-medium ${
              finished ? "text-[var(--muted)] line-through" : "text-[var(--ink)]"
            }`}
          >
            {task.title}
          </span>
          <span className="block text-[length:var(--text-caption)] text-[var(--muted)]">
            {[time, target ? `Target ${target}` : ""].filter(Boolean).join(" · ")}
          </span>
          {task.title_issue ? (
            <span className="block text-[length:var(--text-caption)] text-[var(--warning)]">
              {task.title_issue}
            </span>
          ) : null}
        </button>
        {outcome && task.outcome ? (
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <StatusChip tone={OUTCOME_TONE[task.outcome]}>{outcome}</StatusChip>
            {task.outcome_note ? (
              <span className="text-[length:var(--text-caption)] text-[var(--muted)]">
                {task.outcome_note}
              </span>
            ) : null}
          </div>
        ) : null}
        {menuOpen ? (
          <div
            role="group"
            aria-label={`Actions for ${task.title}`}
            className="mt-2 flex flex-wrap gap-2"
          >
            {finished ? (
              <Button variant="secondary" size="sm" className="min-h-11" onClick={onReopen}>
                Undo and reopen
              </Button>
            ) : null}
            {finished ? (
              <Button variant="secondary" size="sm" className="min-h-11" onClick={onEditOutcome}>
                Change outcome
              </Button>
            ) : null}
            <Button variant="secondary" size="sm" className="min-h-11" onClick={onOpen}>
              Details
            </Button>
          </div>
        ) : null}
      </div>
      <IconButton
        label={`More actions for ${task.title}`}
        aria-expanded={menuOpen}
        className="!h-11 !w-11"
        onClick={onMenu}
      >
        <MoreHorizontal size={18} aria-hidden />
      </IconButton>
    </div>
  );
}

function QuickAdd({ date, onCreated }: { date: string; onCreated: () => Promise<void> }) {
  const [title, setTitle] = useState("");
  const [time, setTime] = useState("");
  const [targetValue, setTargetValue] = useState("");
  const [targetUnit, setTargetUnit] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const nextTitle = title.trim();
    if (!nextTitle) {
      setTitleError("Title is required.");
      return;
    }
    if (nextTitle.length > 256) {
      setTitleError("Title must be 256 characters or fewer.");
      return;
    }
    const target = targetValue.trim() === "" ? null : Number(targetValue);
    if (target !== null && (!Number.isFinite(target) || target <= 0)) {
      setFormError("Target must be a number above zero.");
      return;
    }
    setTitleError(null);
    setFormError(null);
    setCreating(true);
    try {
      await createTask({
        title: nextTitle,
        plan_date: date,
        ...(time ? { due_at: `${date}T${time}` } : {}),
        ...(target !== null ? { target_value: target, target_unit: targetUnit } : {}),
      });
      setTitle("");
      setTime("");
      setTargetValue("");
      setTargetUnit("");
      await onCreated();
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3"
    >
      <div className="flex items-end gap-2">
        <Field
          label="New task"
          htmlFor="new-task-title"
          error={titleError ?? undefined}
          className="min-w-0 flex-1"
        >
          <Input
            id="new-task-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={256}
            placeholder="What do you want to do this day?"
            disabled={creating}
            className="min-h-11"
          />
        </Field>
        <Button
          type="submit"
          loading={creating}
          disabled={creating || !title.trim()}
          className="min-h-11"
        >
          Add task
        </Button>
      </div>
      <details className="text-sm">
        <summary className="min-h-11 cursor-pointer py-2.5 text-[var(--muted)] hover:text-[var(--ink)]">
          Options: time and target
        </summary>
        <div className="mt-2 flex flex-wrap items-end gap-3">
          <Field label="Time (optional)" htmlFor="new-task-time" className="min-w-[8rem]">
            <Input
              id="new-task-time"
              type="time"
              value={time}
              onChange={(event) => setTime(event.target.value)}
              disabled={creating}
              className="min-h-11"
            />
          </Field>
          <Field label="Target (optional)" htmlFor="new-task-target" className="w-28">
            <Input
              id="new-task-target"
              type="number"
              inputMode="decimal"
              min={0}
              step="any"
              value={targetValue}
              onChange={(event) => setTargetValue(event.target.value)}
              placeholder="30"
              disabled={creating}
              className="min-h-11"
            />
          </Field>
          <Field label="Unit" htmlFor="new-task-unit" className="w-36">
            <Input
              id="new-task-unit"
              value={targetUnit}
              maxLength={20}
              onChange={(event) => setTargetUnit(event.target.value)}
              placeholder="push-ups"
              disabled={creating}
              className="min-h-11"
            />
          </Field>
        </div>
      </details>
      {formError ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {formError}
        </p>
      ) : null}
    </form>
  );
}

type DaySummaryCardProps = {
  date: string;
  day: Day;
  drive: DriveSyncStatus | null;
  driveUrl: string | null;
  pct: number | null;
  onCarried: (moved: number, to: string) => Promise<void>;
};

function DaySummaryCard({ date, day, drive, driveUrl, pct, onCarried }: DaySummaryCardProps) {
  const s = day.summary;
  const [confirming, setConfirming] = useState(false);
  const [moving, setMoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const next = addDays(date, 1);
  const nextHeading = dayHeading(next);

  useEffect(() => {
    setConfirming(false);
    setError(null);
  }, [date]);

  async function move() {
    setMoving(true);
    setError(null);
    try {
      const result = await carryOver(date, next);
      setConfirming(false);
      await onCarried(result.moved, result.to);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setMoving(false);
    }
  }

  // Nothing to do when everything is done: the progress line above already says how it went.
  const backupNote =
    Boolean(driveUrl) || Boolean(drive?.enabled && drive.include.daily && s.planned > 0);
  if (s.open === 0 && !backupNote) return null;

  return (
    <Card id="day-summary-title" title="Wrap up">
      <div className="flex flex-col gap-3">
        {s.open > 0 ? (
          confirming ? (
            <div className="flex flex-col gap-2" role="group" aria-label="Confirm carry over">
              <p className="text-sm text-[var(--ink)]">
                {`Move ${s.open} unfinished ${s.open === 1 ? "task" : "tasks"} to ${nextHeading.weekday}?`}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button loading={moving} className="min-h-11" onClick={() => void move()}>
                  {`Move ${s.open}`}
                </Button>
                <Button
                  variant="ghost"
                  className="min-h-11"
                  disabled={moving}
                  onClick={() => setConfirming(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div>
              <Button variant="secondary" className="min-h-11" onClick={() => setConfirming(true)}>
                Carry unfinished to tomorrow
              </Button>
            </div>
          )
        ) : null}
        {error ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}

        {driveUrl ? (
          <a
            href={driveUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-11 items-center text-sm font-medium text-[var(--accent)] underline"
          >
            Saved to Drive
          </a>
        ) : drive?.enabled && drive.include.daily && s.planned > 0 ? (
          <p className="text-sm text-[var(--muted)]">Not backed up yet</p>
        ) : null}
      </div>
    </Card>
  );
}
