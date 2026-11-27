"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FirstRunWizard } from "@/features/onboarding/first-run-wizard";
import { useAuth } from "@/features/auth/use-auth";
import { displayName } from "@/lib/auth/session";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusChip, type StatusChipTone } from "@/components/ui/status-chip";
import { listRecentActivity } from "@/lib/api/activity";
import { apiErrorMessage } from "@/lib/api/client";
import { getMoneyRow } from "@/lib/api/finance";
import { getHabitsToday } from "@/lib/api/habits";
import { skipBriefing, type OnboardingState } from "@/lib/api/onboarding";
import { cancelRun } from "@/lib/api/runs";
import { cachedToday, getToday, type TodayEvent, type TodayPayload } from "@/lib/api/today";
import { todayInsight } from "@/features/module-agent/insights";
import { ModuleAgent } from "@/features/module-agent/module-agent";
import { bucketByDay, sum } from "@/lib/dashboard-stats";
import {
  DailyCard,
  GoalsCard,
  HabitsCard,
  LearnCard,
  ScoreCard,
  MoneyCard,
  NeedsYouCard,
  PlanCard,
} from "./dashboard-cards";

const RUN_STATUS: Record<string, { label: string; tone: StatusChipTone }> = {
  running: { label: "Running", tone: "accent" },
  awaiting_approval: { label: "Waiting for you", tone: "warning" },
};

/**
 * Today is a dashboard: a short sentence, then one summary card per area. Each card shows a
 * headline and at most a few lines; the detail lives one tap away on its own page.
 */
export function TodayPage() {
  const router = useRouter();
  const { status: authStatus } = useAuth();
  const authName = displayName(authStatus?.user);

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
    // Paint the last copy at once; the fresh one replaces it when it arrives.
    const cached = cachedToday();
    if (cached) {
      setToday((prev) => prev ?? cached);
      setOnboarding((prev) => prev ?? cached.onboarding);
    }
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

  useEffect(() => {
    let cancelled = false;
    listRecentActivity()
      .then((events) => {
        if (!cancelled) setWeekActions(sum(bucketByDay(events, 7).map((b) => b.total)));
      })
      .catch(() => {
        /* optional; Today stays calm when activity is unavailable */
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

  const events: TodayEvent[] = today
    ? today.now_next.events.length > 0
      ? today.now_next.events
      : eventsFromBriefing(today)
    : [];
  const tasks = today?.plan.tasks ?? [];
  const overdue = today?.plan.overdue ?? [];
  const needsYou = today?.needs_you ?? [];
  const summary = useMemo(
    () => (today ? oneLineSummary(today, events.length) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [today, events.length],
  );

  async function onSkipBriefing() {
    try {
      const next = await skipBriefing();
      setOnboarding(next);
      setToday((prev) => (prev ? { ...prev, onboarding: next } : prev));
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

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

  const calendarWarning = today?.connections.warnings.find((w) => w.id === "google");
  const calendarNote =
    today && !today.now_next.calendar_connected
      ? {
          message: calendarWarning?.message ?? "Calendar is not connected.",
          label: calendarWarning?.action?.label ?? "Connect",
          href: calendarWarning?.action?.href ?? "/connections",
        }
      : calendarWarning && events.length === 0
        ? {
            message: calendarWarning.message,
            label: calendarWarning.action?.label ?? "Check connection",
            href: calendarWarning.action?.href ?? "/connections",
          }
        : null;
  const otherWarnings = (today?.connections.warnings ?? []).filter((w) => w.id !== "google");
  // Hide "Getting started" once all but one step is done; it is setup, not a daily card.
  const stepsLeft = (onboarding?.items ?? []).filter((item) => !item.done).length;
  const showChecklist = Boolean(onboarding?.show_checklist) && stepsLeft > 1;
  const life = today?.life ?? null;

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
          <p className="mt-1.5 text-sm text-[var(--muted)]" data-testid="today-summary">
            {summary ?? "Here is your day."}
          </p>
        )}
      </header>

      <ModuleAgent
        module="today"
        insight={todayInsight(today)}
        action={
          needsYou.length > 0
            ? { label: "Open Needs you", onClick: () => router.push("/inbox") }
            : tasks.length > 0
              ? { label: "Open Plan", onClick: () => router.push("/tasks") }
              : null
        }
        onDataChanged={() => void load()}
      />

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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <PlanCard
            events={events}
            tasks={tasks}
            overdue={overdue}
            today={today.day?.date ?? ""}
            calendarNote={calendarNote}
            onMoved={() => void load()}
          />
          {today.score ? <ScoreCard score={today.score} /> : null}
          <NeedsYouCard items={needsYou} />
          {today.habits && today.habits.items.length > 0 ? (
            <HabitsCard data={today.habits} onChange={() => void refreshHabits()} />
          ) : null}
          {today.money ? <MoneyCard data={today.money} /> : null}
          {life?.learn ? <LearnCard learn={life.learn} /> : null}
          {life && (life.reading || life.diary) ? <DailyCard life={life} /> : null}
          {today.goals.length > 0 ? <GoalsCard goals={today.goals} /> : null}
        </div>
      ) : loading ? (
        <div
          className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
          role="status"
          aria-label="Loading your day"
        >
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} heightClass="h-40" className="w-full" />
          ))}
        </div>
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
        <p key={warning.id} className="text-sm text-[var(--muted)]">
          {warning.message}{" "}
          {warning.action ? (
            <Link href={warning.action.href} className="text-[var(--accent)] hover:underline">
              {warning.action.label}
            </Link>
          ) : null}
        </p>
      ))}

      {weekActions !== null && weekActions > 0 ? (
        <p className="text-xs text-[var(--muted)]">
          <Link href="/activity" className="inline-flex min-h-11 items-center hover:underline">
            Compass did {weekActions} {weekActions === 1 ? "thing" : "things"} this week
          </Link>
        </p>
      ) : null}
    </div>
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

/**
 * One short sentence built from real numbers. A short backend sentence is kept; the long
 * briefing text is never shown here, because the cards below already say it.
 */
function oneLineSummary(today: TodayPayload, eventCount: number): string | null {
  const given = today.greeting.summary?.trim();
  if (
    given &&
    given.length <= 90 &&
    !given.includes(" — ") &&
    !/^good (morning|afternoon)/i.test(given)
  ) {
    return given;
  }
  const parts: string[] = [];
  const open = today.plan.tasks.filter((t) => t.status !== "done").length;
  if (open > 0) parts.push(`${open} ${open === 1 ? "task" : "tasks"} left`);
  if (eventCount > 0) parts.push(`${eventCount} ${eventCount === 1 ? "event" : "events"}`);
  const overdue = today.plan.overdue?.length ?? 0;
  if (overdue > 0) parts.push(`${overdue} overdue`);
  if (today.habits && today.habits.due > 0)
    parts.push(`${today.habits.done}/${today.habits.due} habits`);
  if (today.needs_you.length > 0) parts.push(`${today.needs_you.length} need you`);
  return parts.length > 0 ? parts.join(" · ") : "A clear day.";
}
