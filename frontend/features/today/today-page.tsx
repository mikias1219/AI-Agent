"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { FirstRunWizard } from "@/features/onboarding/first-run-wizard";
import { useAuth } from "@/features/auth/use-auth";
import { displayName } from "@/lib/auth/session";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { apiErrorMessage } from "@/lib/api/client";
import { latestBriefing } from "@/lib/api/automations";
import { listApprovals } from "@/lib/api/approvals";
import { getOnboarding, skipBriefing, type OnboardingState } from "@/lib/api/onboarding";
import { getStatus } from "@/lib/api/status";
import { listTasks } from "@/lib/api/tasks";
import type { Approval, StatusPayload, Task } from "@/lib/api/types";
import {
  resolveTelegramAgentState,
  telegramOverviewCopy,
} from "@/features/connections/telegram/agent-state";

const SUGGESTIONS = [
  "What should I focus on today?",
  "Create a task to review my inbox this afternoon",
  "Remember that I prefer morning meetings",
  "Summarize what you can help me with",
];

export function TodayPage() {
  const router = useRouter();
  const { status: authStatus } = useAuth();
  const name = displayName(authStatus?.user);

  const [prompt, setPrompt] = useState("");
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [dueTasks, setDueTasks] = useState<Task[]>([]);
  const [overdueTasks, setOverdueTasks] = useState<Task[]>([]);
  const [onboarding, setOnboarding] = useState<OnboardingState | null>(null);
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [briefing, setBriefing] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextApprovals, todayTasks, overdue, nextOnboarding, nextStatus, nextBriefing] =
        await Promise.all([
          listApprovals().catch(() => [] as Approval[]),
          listTasks({ view: "today" }).catch(() => [] as Task[]),
          listTasks({ view: "overdue" }).catch(() => [] as Task[]),
          getOnboarding(),
          getStatus().catch(() => null),
          latestBriefing().catch(() => ({ text: null as string | null })),
        ]);
      setApprovals(nextApprovals.filter((row) => row.actionable));
      setDueTasks(todayTasks);
      setOverdueTasks(overdue);
      setOnboarding(nextOnboarding);
      setStatus(nextStatus);
      setBriefing(nextBriefing.text);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

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
      setOnboarding(await skipBriefing());
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  const telegramState = status
    ? resolveTelegramAgentState({
        configured: status.telegram.configured,
        allowed_chat_ids: status.telegram.allowed_chat_ids,
        managed: status.telegram.managed,
        runtime: status.telegram.runtime,
      })
    : null;
  const telegramCopy = telegramState ? telegramOverviewCopy(telegramState) : null;

  if (onboarding && !onboarding.wizard_completed) {
    return <FirstRunWizard onCompleted={(state) => setOnboarding(state)} />;
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Today</p>
        <h1
          className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {greeting}
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          {new Date().toLocaleDateString(undefined, {
            weekday: "long",
            month: "long",
            day: "numeric",
          })}
        </p>
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
          placeholder="Ask AURA anything…"
          className="w-full resize-none rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm text-[var(--ink)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)]"
        />
        <div className="mt-3 flex flex-wrap gap-2">
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
        </div>
        <div className="mt-3 flex justify-end">
          <Button type="submit">Send</Button>
        </div>
      </form>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Spinner size="sm" /> Loading today…
        </div>
      ) : null}

      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}{" "}
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Retry
          </Button>
        </p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
        <div className="flex flex-col gap-6">
          <section aria-labelledby="today-briefing">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="today-briefing" className="text-sm font-semibold text-[var(--ink)]">
                Daily briefing
              </h2>
              <Link
                href="/routines"
                className="text-xs text-[var(--accent)] underline-offset-2 hover:underline"
              >
                Routines
              </Link>
            </div>
            {!loading && !briefing ? (
              <EmptyState
                title="No briefing yet"
                description="Enable the daily briefing under Routines, or run it now. Empty calendars stay empty."
              />
            ) : null}
            {!loading && briefing ? (
              <pre className="mt-3 whitespace-pre-wrap rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--ink)]">
                {briefing}
              </pre>
            ) : null}
          </section>

          <section aria-labelledby="today-approvals">
            <h2 id="today-approvals" className="text-sm font-semibold text-[var(--ink)]">
              Needs your approval
            </h2>
            {!loading && approvals.length === 0 ? (
              <EmptyState
                title="Nothing waiting"
                description="When AURA drafts a send or change, it will appear here."
              />
            ) : (
              <ul className="mt-3 flex flex-col gap-3">
                {approvals.map((approval) => (
                  <li key={approval.id}>
                    <ApprovalCard approval={approval} onDecided={() => void load()} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="today-agenda">
            <h2 id="today-agenda" className="text-sm font-semibold text-[var(--ink)]">
              Today’s agenda
            </h2>
            <EmptyState
              title="No calendar events loaded"
              description="Connect Google under Connections to show today’s agenda here."
            />
          </section>

          <section aria-labelledby="today-tasks">
            <h2 id="today-tasks" className="text-sm font-semibold text-[var(--ink)]">
              Due and overdue
            </h2>
            {!loading && dueTasks.length === 0 && overdueTasks.length === 0 ? (
              <EmptyState
                title="No due tasks"
                description="Ask AURA to create a task, or add one on the Tasks page."
              />
            ) : (
              <ul className="mt-3 flex flex-col gap-2">
                {[...overdueTasks, ...dueTasks].map((task) => (
                  <li key={task.id}>
                    <Link
                      href="/tasks"
                      className="flex items-center justify-between rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm hover:border-[var(--accent)]"
                    >
                      <span>{task.title}</span>
                      <span className="text-xs text-[var(--muted)]">
                        {task.due_at ? new Date(task.due_at).toLocaleString() : task.status}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="flex flex-col gap-6">
          {onboarding?.show_checklist ? (
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

          <section
            aria-labelledby="today-health"
            className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
          >
            <h2 id="today-health" className="text-sm font-semibold text-[var(--ink)]">
              Connection health
            </h2>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {telegramCopy
                ? `${telegramCopy.value} — ${telegramCopy.detail}`
                : "Agent status unavailable right now."}
            </p>
            <Link
              href="/connections"
              className="mt-3 inline-block text-sm text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Open Connections
            </Link>
          </section>
        </aside>
      </div>
    </div>
  );
}
