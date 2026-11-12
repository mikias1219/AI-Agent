"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { StatusChip } from "@/components/ui/status-chip";
import { apiErrorMessage } from "@/lib/api/client";
import {
  AUTONOMY_LABELS,
  getAgentControl,
  patchAgentControl,
  type AgentControlState,
  type AutonomyPresetId,
} from "@/lib/api/agent-control";

const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

const PRESETS: { id: AutonomyPresetId; blurb: string }[] = [
  {
    id: "ask_first",
    blurb: "Ask before almost every change. Safest default for a new workspace.",
  },
  {
    id: "balanced",
    blurb: "Read freely; prepare drafts and ask before commits that matter.",
  },
  {
    id: "proactive",
    blurb:
      "May suggest and notify within quiet hours and the daily cap. Hard ceilings still need approval.",
  },
];

const BULLETS = [
  "Hard ceilings (new email recipients, delete, spending, sharing, security settings) always need approval — presets never override them.",
  "Pause blocks non-read tools across Chat, Telegram, and Routines until you resume.",
  "Proactive Telegram sends respect quiet hours and the daily proactive budget.",
  "Sessions use HTTP-only cookies; this browser never stores API keys.",
];

export function PermissionsSection() {
  const [state, setState] = useState<AgentControlState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setState(await getAgentControl());
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function setPreset(autonomy_preset: AutonomyPresetId) {
    setBusy(true);
    setError(null);
    try {
      setState(await patchAgentControl({ autonomy_preset }));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function togglePause() {
    if (!state) return;
    setBusy(true);
    setError(null);
    try {
      setState(await patchAgentControl({ paused: !state.paused }));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <section className={panelClass} aria-labelledby="settings-autonomy-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="settings-autonomy-heading" className="text-sm font-semibold text-[var(--ink)]">
              Autonomy
            </h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              How far AURA may go without asking. Presets never bypass hard ceilings.
            </p>
          </div>
          {state ? (
            <StatusChip tone={state.paused ? "warning" : "success"}>
              {state.paused ? "Paused" : "Listening"}
            </StatusChip>
          ) : null}
        </div>

        {loading ? (
          <div className="mt-4 flex items-center gap-2 text-sm text-[var(--muted)]">
            <Spinner size="sm" /> Loading control…
          </div>
        ) : null}

        {error ? (
          <p className="mt-3 text-sm text-[var(--danger)]" role="alert">
            {error}{" "}
            <Button size="sm" variant="secondary" onClick={() => void load()}>
              Retry
            </Button>
          </p>
        ) : null}

        {state ? (
          <>
            <ul className="mt-4 flex flex-col gap-2">
              {PRESETS.map((preset) => {
                const active = state.autonomy_preset === preset.id;
                return (
                  <li key={preset.id}>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void setPreset(preset.id)}
                      className={`w-full rounded-[var(--radius)] border px-3 py-3 text-left transition ${
                        active
                          ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                          : "border-[var(--border)] hover:bg-[var(--canvas)]"
                      }`}
                    >
                      <p className="text-sm font-medium text-[var(--ink)]">
                        {AUTONOMY_LABELS[preset.id]}
                        {active ? " · current" : ""}
                      </p>
                      <p className="mt-1 text-xs text-[var(--muted)]">{preset.blurb}</p>
                    </button>
                  </li>
                );
              })}
            </ul>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant={state.paused ? "primary" : "secondary"}
                loading={busy}
                onClick={() => void togglePause()}
              >
                {state.paused ? "Resume agent" : "Pause agent"}
              </Button>
              <p className="text-xs text-[var(--muted)]">
                Budgets today: {state.budgets.commits_used}/{state.budgets.commits_cap} commits ·{" "}
                {state.budgets.proactive_used}/{state.budgets.proactive_cap} proactive
              </p>
            </div>
          </>
        ) : null}
      </section>

      <section className={panelClass} aria-labelledby="settings-permissions-heading">
        <h2 id="settings-permissions-heading" className="text-sm font-semibold text-[var(--ink)]">
          Access & honesty
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          What this dashboard can and cannot do. No invented toggles.
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-[var(--ink)]">
          {BULLETS.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
