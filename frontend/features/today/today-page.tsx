"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Send, Sparkles } from "lucide-react";
import { FirstRunWizard } from "@/features/onboarding/first-run-wizard";
import { useAuth } from "@/features/auth/use-auth";
import { displayName } from "@/lib/auth/session";
import { Button, buttonClassName } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CompactRow } from "@/components/ui/compact-row";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusChip, type StatusChipTone } from "@/components/ui/status-chip";
import { listRecentActivity } from "@/lib/api/activity";
import { apiErrorMessage } from "@/lib/api/client";
import { skipBriefing, type OnboardingState } from "@/lib/api/onboarding";
import { cancelRun } from "@/lib/api/runs";
import {
  getToday,
  type TodayDay,
  type TodayEvent,
  type TodayLife,
  type TodayPayload,
  type TodayPlanTask,
} from "@/lib/api/today";
import { getHabitsToday } from "@/lib/api/habits";
import { getMoneyRow } from "@/lib/api/finance";
import { HabitsCard, MoneyCard, OverdueNotice } from "./today-rows";
import { scorePercent, showWrapUp } from "@/features/tasks/day-logic";
import { bucketByDay, sum } from "@/lib/dashboard-stats";

const SUGGESTIONS = [
  "Teach me 5 English words",
  "What should I focus on today?",
  "Remember that I prefer morning meetings",
];

const RUN_STATUS: Record<string, { label: string; tone: StatusChipTone }> = {
  running: { label: "Running", tone: "accent" },
  awaiting_approval: { label: "Waiting for you", tone: "warning" },
};

export function formatEventTime(startsAt: string): string {
  if (!startsAt) return "";
  const date = new Date(startsAt);
  if (Number.isNaN(date.getTime())) return startsAt;
  // Date-only values (all-day events) have no clock time.
  if (!startsAt.includes("T")) {
    return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  }
  return date.toLocaleString(undefined, {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function TodayPage() {
  const router = useRouter();
  const { status: authStatus } = useAuth();
  const authName = displayName(authStatus?.user);

  const [prompt, setPrompt] = useState("");
  const [today, setToday] = useState<TodayPayload | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [weekActions, setWeekActions] = useState<number | null>(null);
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getToday();
      setToday(payload);
      setOnboarding(payload.onboarding);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Refresh only the card that changed, so the rest of the page does not move or reload.
  const refreshHabits = useCallback(async () => {
    try {
      const habits = await getHabitsToday();
      setToday((prev) => (prev ? { ...prev, habits } : prev));
    } catch {
      /* the optimistic state stays; the next full load corrects it */
    }
  }, []);
  const refreshMoney = useCallback(async () => {
    try {
      const money = await getMoneyRow();
      setToday((prev) => (prev ? { ...prev, money } : prev));
    } catch {
      /* keep the last row */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    listRecentActivity()
      .then((events) => {
        if (cancelled) return;
        setWeekActions(sum(bucketByDay(events, 7).map((b) => b.total)));
      })
      .catch(() => {
        /* the link is optional; Today stays calm when activity is unavailable */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const name = today?.greeting.name || authName;
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    const when = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
    return name ? `${when}, ${name}` : when;
  }, [name]);
  const greetingSummary = useMemo(
    () => friendlyGreetingSummary(today?.greeting.summary),
    [today?.greeting.summary],
  );

  function submitPrompt(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    router.push(`/chat?q=${encodeURIComponent(trimmed)}`);
  }

  function onComposer(event: FormEvent) {
    event.preventDefault();
    submitPrompt(prompt);
  }

  async function onSkipBriefing() {
    try {
      const next = await skipBriefing();
      setOnboarding(next);
      setToday((prev) => (prev ? { ...prev, onboarding: next } : prev));
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  /** Stop = POST /api/runs/{id}/cancel via cancelRun, then reload the aggregate. */
  async function onStopRun(runId: string) {
    setStopping(true);
    setStopError(null);
    try {
      await cancelRun(runId);
      await load();
    } catch (err) {
      setStopError(apiErrorMessage(err));
    } finally {
      setStopping(false);
    }
  }

  if (onboarding && !onboarding.wizard_completed) {
    return <FirstRunWizard onCompleted={(state) => setOnboarding(state)} />;
  }

  const needsYou = today?.needs_you ?? [];
  const planTasks = today?.plan.tasks ?? [];
  const showChecklist = Boolean(onboarding?.show_checklist);
  const events = today
    ? today.now_next.events.length > 0
      ? today.now_next.events
      : eventsFromBriefing(today)
    : [];
  const briefingHasCalendar = events.length > 0;
  const otherWarnings = (today?.connections.warnings ?? []).filter((w) => w.id !== "google");
  const recentNotes = today?.life?.notes?.recent?.slice(0, 3) ?? [];

  return (
    <div className="mx-auto flex w-full max-w-[var(--content-width)] flex-col gap-5">
      <header className="min-w-0">
        <h1
          className="text-[length:var(--text-display)] leading-[var(--leading-display)] font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {greeting}
        </h1>
        {loading && !today ? (
          <div className="mt-3" role="status" aria-label="Loading summary">
            <Skeleton heightClass="h-4" className="w-2/3" />
          </div>
        ) : (
          <p
            className="mt-1.5 max-w-2xl text-sm leading-6 text-[var(--muted)]"
            data-testid="today-summary"
          >
            {greetingSummary ?? "Here is your day."}
          </p>
        )}
      </header>

      <form
        onSubmit={onComposer}
        className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3"
      >
        <label htmlFor="today-prompt" className="sr-only">
          Ask your agent
        </label>
        <div className="flex items-center gap-2">
          <Sparkles className="ml-1 h-4 w-4 shrink-0 text-[var(--accent)]" aria-hidden />
          <input
            id="today-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask or tell Compass what to do…"
            className="min-h-11 min-w-0 flex-1 bg-transparent text-sm text-[var(--ink)] placeholder:text-[var(--muted)] focus:outline-none"
          />
          <Button type="submit" size="sm" className="min-h-11">
            <Send className="h-3.5 w-3.5" aria-hidden />
            Send
          </Button>
        </div>
        <div className="mt-2 flex flex-wrap gap-2 border-t border-[var(--border)] pt-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => submitPrompt(suggestion)}
              className="min-h-11 rounded-full border border-[var(--border)] bg-[var(--canvas)] px-3 py-1 text-xs text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--ink)] sm:min-h-0"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </form>

      {error ? (
        <div
          className="flex flex-wrap items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm"
          role="alert"
        >
          <span className="text-[var(--danger)]">Today could not be loaded: {error}</span>
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Try again
          </Button>
        </div>
      ) : null}

      {today?.now_next.active_run ? (
        <ActiveRun
          run={today.now_next.active_run}
          stopping={stopping}
          stopError={stopError}
          onStop={(id) => void onStopRun(id)}
        />
      ) : null}

      {today ? (
        <YourDay
          life={today.life ?? null}
          day={today.day ?? null}
          tasksToday={planTasks.length}
          onAsk={submitPrompt}
        />
      ) : loading ? (
        <div
          className="grid grid-cols-2 gap-3 lg:grid-cols-4"
          role="status"
          aria-label="Loading your day"
        >
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} heightClass="h-28" className="w-full" />
          ))}
        </div>
      ) : null}

      {today ? (
        <Card
          id="today-agenda"
          title="Today's plan"
          action={
            <Link
              href="/calendar"
              className="inline-flex min-h-11 items-center text-xs font-medium text-[var(--accent)] hover:underline"
            >
              Calendar
            </Link>
          }
        >
          <Agenda
            today={today}
            events={events}
            calendarHasEvents={briefingHasCalendar}
            onOpenTasks={() => router.push("/tasks")}
            overdue={today.plan.overdue ?? []}
            dayDate={today.day?.date ?? ""}
            onMoved={() => void load()}
          />
        </Card>
      ) : loading ? (
        <Skeleton heightClass="h-32" className="w-full" />
      ) : null}

      {today?.habits ? (
        <HabitsCard data={today.habits} onChange={() => void refreshHabits()} />
      ) : null}

      {needsYou.length > 0 ? (
        <Card
          id="today-needs-you"
          title="Needs you"
          action={
            <Link
              href="/inbox"
              className="inline-flex min-h-11 items-center text-xs font-medium text-[var(--accent)] hover:underline"
            >
              {needsYou.length > 3 ? `See all ${needsYou.length}` : "Open"}
            </Link>
          }
        >
          <ul className="flex flex-col gap-2">
            {needsYou.slice(0, 3).map((item) => (
              <li key={`${item.kind}-${item.id}`}>
                <Link
                  href="/inbox"
                  aria-label={`${item.kind === "approval" ? "Review" : "Open"}: ${item.summary || "request"}`}
                  className="flex min-h-11 items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] px-3 py-2 hover:bg-[var(--canvas)]"
                >
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-[var(--ink)]">
                    {item.summary || item.tool_name || "Approval needed"}
                  </span>
                  <StatusChip tone={item.risk === "high" ? "danger" : "warning"}>
                    {item.kind === "approval" ? "Approval" : "Suggestion"}
                  </StatusChip>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {today?.money ? <MoneyCard data={today.money} onChange={() => void refreshMoney()} /> : null}

      {recentNotes.length > 0 ? (
        <Card
          id="today-notes"
          title="Recent notes"
          action={
            <Link
              href="/library"
              className="inline-flex min-h-11 items-center text-xs font-medium text-[var(--accent)] hover:underline"
            >
              Open Library
            </Link>
          }
        >
          <ul className="flex flex-col gap-2">
            {recentNotes.map((note) => (
              <li key={note.id}>
                <CompactRow
                  title={note.title || "Untitled note"}
                  meta={formatUpdated(note.updated_at)}
                  onClick={() => router.push("/library")}
                />
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {showChecklist && onboarding ? (
        <Card id="today-checklist" title="Getting started">
          <ul className="flex flex-col gap-2 text-sm">
            {onboarding.items.map((item) => (
              <li key={item.id} className="flex items-start gap-2">
                <span aria-hidden>{item.done ? "✓" : "○"}</span>
                <span className={item.done ? "text-[var(--muted)] line-through" : ""}>
                  {item.label}
                </span>
              </li>
            ))}
          </ul>
          {!onboarding.items.find((i) => i.id === "briefing_ready")?.done ? (
            <Button
              className="mt-3"
              size="sm"
              variant="secondary"
              onClick={() => void onSkipBriefing()}
            >
              Skip briefing for now
            </Button>
          ) : null}
        </Card>
      ) : null}

      {otherWarnings.map((warning) => (
        <p
          key={warning.id}
          className="flex flex-wrap items-center gap-2 text-sm text-[var(--muted)]"
        >
          <span>{warning.message}</span>
          {warning.action ? (
            <Link
              href={warning.action.href}
              className="inline-flex min-h-11 items-center text-[var(--accent)] hover:underline"
            >
              {warning.action.label}
            </Link>
          ) : null}
        </p>
      ))}

      {weekActions !== null && weekActions > 0 ? (
        <p className="text-sm text-[var(--muted)]">
          <Link
            href="/activity"
            className="inline-flex min-h-11 items-center text-[var(--accent)] hover:underline"
          >
            Compass did {weekActions} {weekActions === 1 ? "thing" : "things"} this week
          </Link>
        </p>
      ) : null}
    </div>
  );
}

function DayCard({
  label,
  value,
  hint,
  action,
  extra,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  action?: { href: string; label: string };
  extra?: ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-1 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3">
      <p className="text-xs font-medium text-[var(--muted)]">{label}</p>
      <p className="truncate text-xl font-semibold text-[var(--ink)]">{value}</p>
      {hint ? <p className="truncate text-xs text-[var(--muted)]">{hint}</p> : null}
      {extra}
      {action ? (
        <Link
          href={action.href}
          className={`${buttonClassName("secondary", "sm")} mt-auto min-h-11 justify-center`}
        >
          {action.label}
        </Link>
      ) : null}
    </div>
  );
}

function YourDay({
  life,
  day,
  tasksToday,
  onAsk,
}: {
  life: TodayLife | null;
  day: TodayDay | null;
  tasksToday: number;
  onAsk: (text: string) => void;
}) {
  const learn = life?.learn;
  const reading = life?.reading;
  const diary = life?.diary;
  const hasLife = Boolean(learn || reading || diary);
  const summary = day?.summary ?? null;
  const planned = summary?.planned ?? tasksToday;
  const openCount = summary?.open ?? 0;
  const pct = scorePercent(summary?.score);

  // Without notes, learning or reading there is nothing here that the plan card does not
  // already say, so show only the one-line tip instead of a lone card.
  if (!hasLife) {
    return (
      <p className="text-sm text-[var(--muted)]">
        New here? Try:{" "}
        <button
          type="button"
          onClick={() => onAsk("Teach me 5 English words")}
          className="min-h-11 text-[var(--accent)] hover:underline"
        >
          teach me 5 English words
        </button>
        , or write your first note in the{" "}
        <Link href="/library" className="text-[var(--accent)] hover:underline">
          Library
        </Link>
        .
        {showWrapUp(openCount) ? (
          <>
            {" "}
            <Link href="/tasks" className="text-[var(--accent)] hover:underline">
              Wrap up the day
            </Link>
          </>
        ) : null}
      </p>
    );
  }

  return (
    <section aria-label="Your day" className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold text-[var(--muted)]">Your day</h2>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(13rem,1fr))] gap-3">
        {learn ? (
          <DayCard
            label="Words to review"
            value={learn.due}
            hint={
              learn.due > 0
                ? (learn.next_term ?? "Ready when you are")
                : learn.total > 0
                  ? "All caught up"
                  : "No words yet"
            }
            action={{ href: "/learn", label: learn.due > 0 ? "Review" : "Open Learn" }}
          />
        ) : null}
        {reading ? (
          <DayCard
            label="Reading"
            value={reading.next ?? "No plan yet"}
            hint={
              reading.read_today
                ? `Read today${reading.streak_days > 0 ? ` · ${reading.streak_days}-day streak` : ""}`
                : (reading.plan_name ?? undefined)
            }
            action={{
              href: "/learn?tab=reading",
              label: reading.read_today || !reading.next ? "Open reading" : "Mark as read",
            }}
          />
        ) : null}
        {diary ? (
          <DayCard
            label="Diary"
            value={
              diary.wrote_today
                ? "Written"
                : diary.streak_days > 0
                  ? `${diary.streak_days}-day streak`
                  : "Not yet"
            }
            hint={
              diary.wrote_today ? `${diary.streak_days}-day streak` : "Keep it short and honest"
            }
            action={{
              href: "/library?new=diary",
              label: diary.wrote_today ? "Add more" : "Write today's entry",
            }}
          />
        ) : null}
        <DayCard
          label="Tasks today"
          value={summary ? `${summary.done} of ${planned}` : tasksToday}
          hint={
            planned > 0
              ? summary
                ? `done${pct !== null ? `, score ${pct}%` : ""}`
                : "Due or planned today"
              : "Nothing planned"
          }
          extra={
            showWrapUp(openCount) ? (
              <Link
                href="/tasks"
                className="inline-flex min-h-11 items-center text-xs font-medium text-[var(--accent)] hover:underline"
              >
                Wrap up the day
              </Link>
            ) : null
          }
          action={{ href: "/tasks", label: "Open Plan" }}
        />
      </div>
      {!hasLife ? (
        <p className="text-sm text-[var(--muted)]">
          New here? Try:{" "}
          <button
            type="button"
            onClick={() => onAsk("Teach me 5 English words")}
            className="min-h-11 text-[var(--accent)] hover:underline"
          >
            teach me 5 English words
          </button>
          , or write your first note in the{" "}
          <Link href="/library" className="text-[var(--accent)] hover:underline">
            Library
          </Link>
          .
        </p>
      ) : null}
    </section>
  );
}

function ActiveRun({
  run,
  stopping,
  stopError,
  onStop,
}: {
  run: NonNullable<TodayPayload["now_next"]["active_run"]>;
  stopping: boolean;
  stopError: string | null;
  onStop: (runId: string) => void;
}) {
  const runStatus = RUN_STATUS[run.status] ?? { label: run.status, tone: "neutral" as const };
  return (
    <div className="flex flex-col gap-1">
      <div
        className="flex min-h-11 items-center gap-3 rounded-[var(--radius)] border border-[var(--accent-soft)] bg-[var(--accent-soft)] px-3 py-2.5"
        data-testid="today-active-run"
      >
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-[var(--ink)]">
            Compass is working: {run.input || "a request"}
          </p>
          <p className="truncate text-xs text-[var(--muted)]">
            {run.origin ? `Started from ${run.origin}` : "Active run"}
          </p>
        </div>
        <StatusChip tone={runStatus.tone}>{runStatus.label}</StatusChip>
        <Button
          size="sm"
          variant="secondary"
          className="min-h-11"
          disabled={stopping}
          onClick={() => onStop(run.id)}
        >
          {stopping ? "Stopping…" : "Stop"}
        </Button>
      </div>
      {stopError ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          Could not stop the run: {stopError}
        </p>
      ) : null}
    </div>
  );
}

function Agenda({
  today,
  events,
  calendarHasEvents,
  onOpenTasks,
  overdue,
  dayDate,
  onMoved,
}: {
  overdue: TodayPlanTask[];
  dayDate: string;
  onMoved: () => void;
  today: TodayPayload;
  events: TodayEvent[];
  calendarHasEvents: boolean;
  onOpenTasks: () => void;
}) {
  const connected = today.now_next.calendar_connected;
  const calendarWarning = today.connections.warnings.find((w) => w.id === "google");
  const tasks = today.plan.tasks.slice(0, 5);
  const showWarning = Boolean(calendarWarning) && !calendarHasEvents;

  return (
    <div className="flex flex-col gap-2">
      <OverdueNotice tasks={overdue} today={dayDate} onChange={onMoved} />
      {events.map((event) => (
        <CompactRow
          key={event.id || `${event.title}-${event.startsAt}`}
          title={event.title}
          meta={[formatEventTime(event.startsAt), event.location].filter(Boolean).join(" · ")}
          chip={<StatusChip tone="accent">Event</StatusChip>}
        />
      ))}
      {tasks.map((task) => (
        <CompactRow
          key={task.id}
          title={task.title}
          meta={
            task.due_at ? `Due ${formatEventTime(task.due_at)}` : (task.project ?? "No due date")
          }
          chip={task.priority === "high" ? <StatusChip tone="warning">High</StatusChip> : undefined}
          onClick={onOpenTasks}
        />
      ))}
      {!connected ? (
        <ConnectCallout
          message={calendarWarning?.message ?? "Calendar is not connected."}
          label={calendarWarning?.action?.label ?? "Connect"}
          href={calendarWarning?.action?.href ?? "/connections"}
        />
      ) : showWarning ? (
        <ConnectCallout
          message={calendarWarning!.message}
          label={calendarWarning!.action?.label ?? "Check connection"}
          href={calendarWarning!.action?.href ?? "/connections"}
        />
      ) : null}
      {events.length === 0 &&
      tasks.length === 0 &&
      overdue.length === 0 &&
      connected &&
      !showWarning ? (
        <EmptyState
          compact
          title="A clear day"
          description="Nothing scheduled and no tasks due. Ask Compass to plan something, or enjoy the space."
        />
      ) : null}
    </div>
  );
}

function ConnectCallout({
  message,
  label,
  href,
}: {
  message: string;
  label: string;
  href: string;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius)] border border-dashed border-[var(--border)] bg-[var(--surface)] px-3 py-2">
      <p className="text-sm text-[var(--muted)]">{message}</p>
      <Link href={href} className={`${buttonClassName("secondary", "sm")} min-h-11`}>
        {label}
      </Link>
    </div>
  );
}

function eventsFromBriefing(today: TodayPayload): TodayEvent[] {
  const calendar = today.briefing.sections?.find((s) => s.id === "calendar");
  if (!calendar || (calendar.status !== "ok" && calendar.status !== "empty")) return [];
  return calendar.items.slice(0, 3).map((item, index) => ({
    id: `briefing-cal-${index}`,
    title: item.title,
    startsAt: item.time || "",
    location: "",
  }));
}

function formatUpdated(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return `Updated ${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
}

function friendlyGreetingSummary(raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null;
  const lowered = raw.toLowerCase();
  if (
    lowered.includes("inference http") ||
    lowered.includes("invalid 'tools") ||
    lowered.includes("provider returned") ||
    lowered.includes('"error"') ||
    lowered.includes("could not finish") ||
    lowered.includes("briefing sources were gathered")
  ) {
    return null;
  }
  return raw.trim().length > 280 ? `${raw.trim().slice(0, 277)}…` : raw.trim();
}
