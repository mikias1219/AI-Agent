"use client";

import { formatDateTime } from "@/lib/format-date";
import { useCallback, useEffect, useState } from "react";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SkeletonRows } from "@/components/ui/skeleton";
import { apiErrorMessage } from "@/lib/api/client";
import {
  listAutomations,
  patchAutomation,
  runAutomation,
  type Automation,
} from "@/lib/api/automations";

export type AutomationsPageProps = {
  embedded?: boolean;
};

const ROUTINE_COPY: Record<string, { label: string; blurb: string }> = {
  daily_briefing: {
    label: "Morning briefing",
    blurb: "Calendar, tasks, approvals and email into one morning summary.",
  },
  inbox_triage: {
    label: "Inbox triage",
    blurb: "Reads recent mail and proposes reply drafts under Needs you → Mail replies.",
  },
  evening_wrapup: {
    label: "Evening wrap-up",
    blurb: "What moved today and what still needs you tomorrow.",
  },
  weekly_review: {
    label: "Weekly review",
    blurb: "Goals, open plans and overdue work for the week (Mondays).",
  },
  deadline_guard: {
    label: "Deadline guard",
    blurb: "Surfaces overdue and due-today tasks as suggestions.",
  },
};

function routineLabel(kind: string): string {
  return ROUTINE_COPY[kind]?.label ?? kind.replaceAll("_", " ");
}

function scheduleWords(item: Automation): string {
  const time = item.schedule_time ? ` at ${item.schedule_time}` : "";
  const when = item.kind === "weekly_review" ? "Every Monday" : "Every day";
  return item.enabled ? `${when}${time}` : `Off. Would run ${when.toLowerCase()}${time}`;
}

export function AutomationsPage(_props: AutomationsPageProps = {}) {
  const [items, setItems] = useState<Automation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listAutomations());
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(item: Automation) {
    setBusyId(item.id);
    try {
      const updated = await patchAutomation(item.id, { enabled: !item.enabled });
      setItems((prev) => prev.map((row) => (row.id === item.id ? updated : row)));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function saveTime(item: Automation, schedule_time: string) {
    setBusyId(item.id);
    try {
      const updated = await patchAutomation(item.id, { schedule_time });
      setItems((prev) => prev.map((row) => (row.id === item.id ? updated : row)));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function saveQuietAndCap(
    item: Automation,
    patch: { quiet_hours_start?: string; quiet_hours_end?: string; daily_cap?: number },
  ) {
    setBusyId(item.id);
    try {
      const updated = await patchAutomation(item.id, patch);
      setItems((prev) => prev.map((row) => (row.id === item.id ? updated : row)));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function runNow(item: Automation) {
    setBusyId(item.id);
    try {
      const result = await runAutomation(item.id);
      if (result.automation) {
        setItems((prev) => prev.map((row) => (row.id === item.id ? result.automation! : row)));
      } else {
        await load();
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {loading ? <SkeletonRows count={3} /> : null}

      {error ? (
        <Banner tone="danger" role="alert">
          <div className="flex flex-wrap items-center gap-3">
            <span>Something went wrong: {error}</span>
            <Button size="sm" variant="secondary" onClick={() => void load()}>
              Try again
            </Button>
          </div>
        </Banner>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No routines yet"
          description="Routines are scheduled jobs such as a morning briefing. Every run uses the same approval gates as chat, and Compass never invents events."
          action={<Button onClick={() => void load()}>Check again</Button>}
        />
      ) : null}

      {!loading && items.length > 0 ? (
        <ul className="flex flex-col gap-3">
          {items.map((item) => {
            const label = routineLabel(item.kind);
            const busy = busyId === item.id;
            return (
              <li key={item.id}>
                <Card
                  title={label}
                  description={ROUTINE_COPY[item.kind]?.blurb}
                  action={
                    <button
                      type="button"
                      role="switch"
                      aria-checked={item.enabled}
                      aria-label={`${label} ${item.enabled ? "on" : "off"}`}
                      disabled={busy}
                      onClick={() => void toggle(item)}
                      className="inline-flex min-h-11 items-center gap-2 rounded-full px-1 text-sm text-[var(--ink)] focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none disabled:opacity-60"
                    >
                      <span
                        aria-hidden
                        className={`relative inline-block h-6 w-11 rounded-full border transition ${
                          item.enabled
                            ? "border-[var(--accent)] bg-[var(--accent)]"
                            : "border-[var(--border)] bg-[var(--canvas)]"
                        }`}
                      >
                        <span
                          className={`absolute top-0.5 h-4.5 w-4.5 rounded-full bg-[var(--surface)] shadow transition-all ${
                            item.enabled ? "left-5.5" : "left-0.5"
                          }`}
                        />
                      </span>
                      {item.enabled ? "On" : "Off"}
                    </button>
                  }
                >
                  <div className="flex flex-col gap-3">
                    <p className="text-sm text-[var(--ink)]">{scheduleWords(item)}</p>
                    <p className="text-xs text-[var(--muted)]">
                      {item.last_run_at
                        ? `Last ran ${formatDateTime(item.last_run_at)}`
                        : "Has not run yet"}
                    </p>
                    {item.last_result ? (
                      <details className="text-xs">
                        <summary className="min-h-8 cursor-pointer text-[var(--muted)] hover:text-[var(--ink)]">
                          Last result
                        </summary>
                        <pre className="mt-1 max-h-48 overflow-auto rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] p-3 whitespace-pre-wrap text-[var(--ink)]">
                          {item.last_result}
                        </pre>
                      </details>
                    ) : null}
                    <div>
                      <Button
                        className="min-h-11 sm:min-h-0"
                        size="sm"
                        loading={busy}
                        disabled={!item.enabled}
                        onClick={() => void runNow(item)}
                      >
                        Run now
                      </Button>
                    </div>
                    <details className="text-sm">
                      <summary className="min-h-8 cursor-pointer text-[var(--muted)] hover:text-[var(--ink)]">
                        Advanced settings
                      </summary>
                      <div className="mt-3 grid max-w-xl gap-3 sm:grid-cols-2">
                        <Field label="Local time (HH:MM)" htmlFor={`sched-${item.id}`}>
                          <Input
                            id={`sched-${item.id}`}
                            defaultValue={item.schedule_time}
                            onBlur={(e) => {
                              const value = e.target.value.trim();
                              if (value && value !== item.schedule_time) void saveTime(item, value);
                            }}
                          />
                        </Field>
                        <Field label="Daily proactive cap (0 = default)" htmlFor={`cap-${item.id}`}>
                          <Input
                            id={`cap-${item.id}`}
                            type="number"
                            min={0}
                            max={100}
                            defaultValue={String(item.daily_cap ?? 0)}
                            onBlur={(e) => {
                              const value = Number(e.target.value);
                              if (!Number.isNaN(value) && value !== item.daily_cap) {
                                void saveQuietAndCap(item, { daily_cap: value });
                              }
                            }}
                          />
                        </Field>
                        <Field label="Quiet hours start" htmlFor={`qh-s-${item.id}`}>
                          <Input
                            id={`qh-s-${item.id}`}
                            placeholder="22:00"
                            defaultValue={item.quiet_hours_start || ""}
                            onBlur={(e) => {
                              const value = e.target.value.trim();
                              if (value !== (item.quiet_hours_start || "")) {
                                void saveQuietAndCap(item, { quiet_hours_start: value });
                              }
                            }}
                          />
                        </Field>
                        <Field label="Quiet hours end" htmlFor={`qh-e-${item.id}`}>
                          <Input
                            id={`qh-e-${item.id}`}
                            placeholder="07:00"
                            defaultValue={item.quiet_hours_end || ""}
                            onBlur={(e) => {
                              const value = e.target.value.trim();
                              if (value !== (item.quiet_hours_end || "")) {
                                void saveQuietAndCap(item, { quiet_hours_end: value });
                              }
                            }}
                          />
                        </Field>
                      </div>
                      <p className="mt-2 text-xs text-[var(--muted)]">
                        External proactive sends (Telegram) respect pause, quiet hours, and the
                        daily cap. Inbox updates still run.
                      </p>
                      {item.last_run_id ? (
                        <p className="mt-1 text-xs text-[var(--muted)]">
                          Run id {item.last_run_id}
                        </p>
                      ) : null}
                    </details>
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
