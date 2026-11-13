"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FirstRunWizard } from "@/features/onboarding/first-run-wizard";
import { useAuth } from "@/features/auth/use-auth";
import { displayName } from "@/lib/auth/session";
import { Button } from "@/components/ui/button";
import { CompactRow } from "@/components/ui/compact-row";
import { DensityToggle } from "@/components/ui/density-toggle";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusChip, type StatusChipTone } from "@/components/ui/status-chip";
import { apiErrorMessage } from "@/lib/api/client";
import { skipBriefing, type OnboardingState } from "@/lib/api/onboarding";
import { cancelRun } from "@/lib/api/runs";
import {
  getToday,
  type TodayBriefingSection,
  type TodayEvent,
  type TodayPayload,
} from "@/lib/api/today";

const SUGGESTIONS = [
  "What should I focus on today?",
  "Create a task to review my inbox this afternoon",
  "Remember that I prefer morning meetings",
];

const SECTION_STATUS: Record<string, { label: string; tone: StatusChipTone }> = {
  empty: { label: "Nothing found", tone: "neutral" },
  not_connected: { label: "Not connected", tone: "warning" },
  unavailable: { label: "Unavailable", tone: "warning" },
  error: { label: "Error", tone: "danger" },
};

const RUN_STATUS: Record<string, { label: string; tone: StatusChipTone }> = {
  running: { label: "Running", tone: "accent" },
  awaiting_approval: { label: "Waiting for you", tone: "warning" },
};

const WARNING_TONE: Record<string, StatusChipTone> = {
  info: "neutral",
  warning: "warning",
  error: "danger",
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

  const name = today?.greeting.name || authName;
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    const when = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
    return name ? `${when}, ${name}` : when;
  }, [name]);

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

  const needsYou = today?.needs_you.slice(0, 3) ?? [];
  const warnings = today?.connections.warnings ?? [];
  const sinceLast = today?.since_last_looked ?? [];
  const goals = today?.goals ?? [];
  const summary = today?.greeting.summary || null;
  const showChecklist = Boolean(onboarding?.show_checklist);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-[var(--row-gap)]">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h1
            className="text-[22px] leading-[30px] font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {greeting}
          </h1>
          {loading && !today ? (
            <SkeletonLines count={1} label="Loading summary" />
          ) : summary ? (
            <p className="mt-2 max-w-2xl text-sm text-[var(--ink)]" data-testid="today-summary">
              {summary}
            </p>
          ) : null}
        </div>
        <DensityToggle />
      </header>

      <form
        onSubmit={onComposer}
        className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
      >
        <label htmlFor="today-prompt" className="sr-only">
          Ask your agent
        </label>
        <textarea
          id="today-prompt"
          rows={2}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask or tell AURA…"
          className="w-full resize-none rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm text-[var(--ink)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)]"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <Button
              key={suggestion}
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => submitPrompt(suggestion)}
            >
              {suggestion}
            </Button>
          ))}
          <Button type="submit" className="ml-auto">
            Send
          </Button>
        </div>
      </form>

      {error ? (
        <div
          className="flex flex-wrap items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm"
          role="alert"
        >
          <span className="text-[var(--danger)]">Today could not be loaded: {error}</span>
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
        <div className="flex flex-col gap-6">
          {needsYou.length > 0 ? (
            <Section id="today-needs-you" title="Needs you">
              <ul className="flex flex-col gap-2">
                {needsYou.map((item) => (
                  <li key={`${item.kind}-${item.id}`}>
                    <CompactRow
                      title={item.summary || item.tool_name || "Approval needed"}
                      meta={needsYouMeta(item.kind, item.risk, item.expires_at)}
                      chip={
                        <Link
                          href="/inbox"
                          className="rounded-[var(--radius)] border border-[var(--border)] px-2.5 py-1 text-xs font-medium text-[var(--accent)] hover:border-[var(--accent)]"
                        >
                          {item.kind === "approval" ? "Review" : "Open"}
                        </Link>
                      }
                    />
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {loading && !today ? (
            <>
              <SkeletonSection title="Now and next" />
              <SkeletonSection title="Today’s plan" />
              <SkeletonSection title="Daily briefing" />
            </>
          ) : null}

          {today ? (
            <>
              <NowNext
                today={today}
                stopping={stopping}
                stopError={stopError}
                onStop={(id) => void onStopRun(id)}
              />

              <Section
                id="today-plan"
                title="Today’s plan"
                action={
                  <Link
                    href="/tasks"
                    className="text-xs text-[var(--accent)] underline-offset-2 hover:underline"
                  >
                    All tasks
                  </Link>
                }
              >
                {today.plan.tasks.length === 0 ? (
                  <EmptyState
                    title="No tasks due today"
                    description="Ask AURA to create a task, or add one on the Tasks page."
                  />
                ) : (
                  <ul className="flex flex-col gap-2">
                    {today.plan.tasks.map((task) => (
                      <li key={task.id}>
                        <CompactRow
                          title={task.title}
                          meta={
                            [
                              task.due_at ? new Date(task.due_at).toLocaleString() : null,
                              task.project,
                            ]
                              .filter(Boolean)
                              .join(" · ") || undefined
                          }
                          chip={
                            <StatusChip tone={task.priority === "high" ? "warning" : "neutral"}>
                              {task.priority}
                            </StatusChip>
                          }
                          onClick={() => router.push("/tasks")}
                        />
                      </li>
                    ))}
                  </ul>
                )}
              </Section>

              {goals.length > 0 ? (
                <Section id="today-goals" title="In progress">
                  <p className="text-sm text-[var(--muted)]">
                    {goals.length} active {goals.length === 1 ? "goal" : "goals"}.{" "}
                    <Link href="/goals" className="text-[var(--accent)] hover:underline">
                      Open Goals
                    </Link>
                  </p>
                </Section>
              ) : null}

              {sinceLast.length > 0 ? (
                <Section id="today-since" title="Since you last looked">
                  <p className="text-sm text-[var(--muted)]">
                    {sinceLast.length} new {sinceLast.length === 1 ? "update" : "updates"}.{" "}
                    <Link href="/activity" className="text-[var(--accent)] hover:underline">
                      Open Activity
                    </Link>
                  </p>
                </Section>
              ) : null}

              <BriefingSection briefing={today.briefing} />
            </>
          ) : null}
        </div>

        <aside className="flex flex-col gap-6">
          {loading && !today ? <SkeletonSection title="Getting started" /> : null}

          {showChecklist && onboarding ? (
            <section
              aria-labelledby="today-checklist"
              className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
            >
              <h2 id="today-checklist" className="text-sm font-semibold text-[var(--ink)]">
                Getting started
              </h2>
              <ul className="mt-3 flex flex-col gap-2 text-sm">
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
            </section>
          ) : null}

          {warnings.length > 0 ? (
            <section
              aria-labelledby="today-connections"
              className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
            >
              <h2 id="today-connections" className="text-sm font-semibold text-[var(--ink)]">
                Connections
              </h2>
              <ul className="mt-3 flex flex-col gap-3">
                {warnings.map((warning) => (
                  <li key={warning.id} className="flex flex-col gap-1.5 text-sm">
                    <div className="flex items-start gap-2">
                      <StatusChip tone={WARNING_TONE[warning.severity] ?? "neutral"}>
                        {warning.severity}
                      </StatusChip>
                      <span className="text-[var(--ink)]">{warning.message}</span>
                    </div>
                    {warning.action ? (
                      <Link
                        href={warning.action.href}
                        className="text-[var(--accent)] underline-offset-2 hover:underline"
                      >
                        {warning.action.label}
                      </Link>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

function needsYouMeta(kind: string, risk?: string, expiresAt?: string | null): string {
  const parts = [kind === "approval" ? "Approval" : "Suggestion"];
  if (risk) parts.push(`${risk} risk`);
  if (expiresAt) {
    const when = new Date(expiresAt);
    if (!Number.isNaN(when.getTime())) parts.push(`expires ${when.toLocaleTimeString()}`);
  }
  return parts.join(" · ");
}

function NowNext({
  today,
  stopping,
  stopError,
  onStop,
}: {
  today: TodayPayload;
  stopping: boolean;
  stopError: string | null;
  onStop: (runId: string) => void;
}) {
  const { events, calendar_connected: connected, active_run: run } = today.now_next;
  const calendarWarning = today.connections.warnings.find((w) => w.id === "google");
  const runStatus = run ? (RUN_STATUS[run.status] ?? { label: run.status, tone: "neutral" }) : null;

  return (
    <Section id="today-now-next" title="Now and next">
      <div className="flex flex-col gap-2">
        {run && runStatus ? (
          <div
            className="flex min-h-11 items-center gap-3 rounded-[var(--radius)] border border-[var(--accent-soft)] bg-[var(--accent-soft)] px-3 py-2.5"
            data-testid="today-active-run"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-[var(--ink)]">
                AURA is working: {run.input || "a request"}
              </p>
              <p className="truncate text-xs text-[var(--muted)]">
                {run.origin ? `Started from ${run.origin}` : "Active run"}
              </p>
            </div>
            <StatusChip tone={runStatus.tone}>{runStatus.label}</StatusChip>
            <Button
              size="sm"
              variant="secondary"
              disabled={stopping}
              onClick={() => onStop(run.id)}
            >
              {stopping ? "Stopping…" : "Stop"}
            </Button>
          </div>
        ) : null}
        {stopError ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            Could not stop the run: {stopError}
          </p>
        ) : null}

        {events.map((event) => (
          <EventRow key={event.id || `${event.title}-${event.startsAt}`} event={event} />
        ))}

        {!connected ? (
          <ConnectCallout
            message={calendarWarning?.message ?? "Calendar is not connected."}
            label={calendarWarning?.action?.label ?? "Connect"}
            href={calendarWarning?.action?.href ?? "/connections"}
          />
        ) : calendarWarning && events.length === 0 ? (
          <ConnectCallout
            message={calendarWarning.message}
            label={calendarWarning.action?.label ?? "Check connection"}
            href={calendarWarning.action?.href ?? "/connections"}
          />
        ) : events.length === 0 && !run ? (
          <p className="text-sm text-[var(--muted)]">No upcoming events on your calendar.</p>
        ) : null}
      </div>
    </Section>
  );
}

function EventRow({ event }: { event: TodayEvent }) {
  return (
    <CompactRow
      title={event.title}
      meta={[formatEventTime(event.startsAt), event.location].filter(Boolean).join(" · ")}
      chip={<StatusChip tone="accent">Event</StatusChip>}
    />
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
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius)] border border-dashed border-[var(--border)] bg-[var(--surface)] px-3 py-3">
      <p className="text-sm text-[var(--muted)]">{message}</p>
      <Link
        href={href}
        className="rounded-[var(--radius)] border border-[var(--border)] px-2.5 py-1 text-xs font-medium text-[var(--accent)] hover:border-[var(--accent)]"
      >
        {label}
      </Link>
    </div>
  );
}

function BriefingSection({ briefing }: { briefing: TodayPayload["briefing"] }) {
  const sections = briefing.sections ?? [];
  const hasContent = sections.length > 0 || Boolean(briefing.text);
  return (
    <Section
      id="today-briefing"
      title="Daily briefing"
      action={
        <Link
          href="/routines"
          className="text-xs text-[var(--accent)] underline-offset-2 hover:underline"
        >
          Routines
        </Link>
      }
    >
      {!hasContent ? (
        <EmptyState
          title="No briefing yet"
          description="Enable the daily briefing under Routines, or run it now."
        />
      ) : sections.length > 0 ? (
        <div className="flex flex-col gap-3">
          {sections.map((section) => (
            <BriefingBlock key={section.id} section={section} />
          ))}
        </div>
      ) : (
        <div className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm whitespace-pre-wrap text-[var(--ink)]">
          {briefing.text}
        </div>
      )}
    </Section>
  );
}

function BriefingBlock({ section }: { section: TodayBriefingSection }) {
  const status = SECTION_STATUS[section.status];
  return (
    <div
      className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
      data-testid={`briefing-section-${section.id}`}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--ink)]">{section.heading}</h3>
        {status ? <StatusChip tone={status.tone}>{status.label}</StatusChip> : null}
      </div>
      {section.summary ? (
        <p className="mt-1 text-sm text-[var(--muted)]">{section.summary}</p>
      ) : null}
      {section.items.length > 0 ? (
        <ul className="mt-3 flex flex-col gap-1.5 text-sm">
          {section.items.map((item, index) => (
            <li key={`${item.title}-${index}`} className="flex gap-2">
              {item.time ? (
                <span className="w-16 shrink-0 text-xs text-[var(--muted)]">{item.time}</span>
              ) : null}
              <span className="text-[var(--ink)]">
                {item.title}
                {item.detail ? <span className="text-[var(--muted)]"> — {item.detail}</span> : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function Section({
  id,
  title,
  action,
  children,
}: {
  id: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={id}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id={id} className="text-sm font-semibold text-[var(--ink)]">
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function SkeletonLines({ count, label }: { count: number; label: string }) {
  return (
    <div className="mt-3 flex flex-col gap-2" role="status" aria-label={label}>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="h-4 w-2/3 animate-pulse rounded bg-[var(--border)]" />
      ))}
    </div>
  );
}

function SkeletonSection({ title }: { title: string }) {
  return (
    <section aria-busy="true" aria-label={`${title} (loading)`}>
      <h2 className="mb-3 text-sm font-semibold text-[var(--muted)]">{title}</h2>
      <div className="flex flex-col gap-2">
        <div className="h-11 animate-pulse rounded-[var(--radius)] bg-[var(--border)]" />
        <div className="h-11 animate-pulse rounded-[var(--radius)] bg-[var(--border)] opacity-60" />
      </div>
    </section>
  );
}
