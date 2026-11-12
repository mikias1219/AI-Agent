"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { apiErrorMessage } from "@/lib/api/client";
import {
  listAutomations,
  patchAutomation,
  runAutomation,
  type Automation,
} from "@/lib/api/automations";

export function AutomationsPage() {
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
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Routines</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Scheduled work
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Daily briefing and reminders use the same approval gates as chat. Empty calendars stay
          empty — AURA never invents events.
        </p>
      </header>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Spinner size="sm" /> Loading routines…
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

      {!loading && items.length === 0 ? (
        <EmptyState
          title="No routines"
          description="The daily briefing appears here after the first load."
        />
      ) : null}

      <ul className="flex flex-col gap-4">
        {items.map((item) => (
          <li
            key={item.id}
            className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold text-[var(--ink)]">
                  {item.kind === "daily_briefing" ? "Daily briefing" : item.kind}
                </h2>
                <p className="text-xs text-[var(--muted)]">
                  {item.enabled ? "Enabled" : "Disabled"}
                  {item.last_run_at
                    ? ` · Last run ${new Date(item.last_run_at).toLocaleString()}`
                    : " · Not run yet"}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busyId === item.id}
                  onClick={() => void toggle(item)}
                >
                  {item.enabled ? "Disable" : "Enable"}
                </Button>
                <Button
                  size="sm"
                  disabled={busyId === item.id || !item.enabled}
                  onClick={() => void runNow(item)}
                >
                  Run now
                </Button>
              </div>
            </div>
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
              External proactive sends (Telegram) respect pause, quiet hours, and the daily cap.
              Inbox updates still run.
            </p>
            {item.last_result ? (
              <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] p-3 text-xs text-[var(--ink)]">
                {item.last_result}
              </pre>
            ) : null}
            {item.last_run_id ? (
              <p className="mt-2 text-xs text-[var(--muted)]">Run id {item.last_run_id}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
