"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { StatusChip } from "@/components/ui/status-chip";
import { apiErrorMessage } from "@/lib/api/client";
import {
  AUTONOMY_BLURBS,
  AUTONOMY_IN_EFFECT,
  AUTONOMY_LABELS,
  AUTONOMY_TODAY,
  getAgentControl,
  getAgentPermissions,
  patchAgentControl,
  type AgentControlState,
  type AgentPermissionTool,
  type AutonomyPresetId,
  type ToolPermissionMode,
} from "@/lib/api/agent-control";

const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

const PRESETS: AutonomyPresetId[] = ["ask_first", "balanced", "proactive"];

const BULLETS = [
  "Sending an email or a message, creating or changing a calendar event, cancelling a reminder, forgetting a memory and deleting anything always wait for your approval.",
  "Reading, drafting, and creating or updating your own tasks, reminders and goals run without asking and are recorded in Activity.",
  "Pause stops everything except reading, across Chat, Telegram and Routines, until you resume.",
  "Scheduled messages respect quiet hours and the daily limit.",
  "Sessions use HTTP-only cookies; this browser never stores API keys.",
];

const MODES: ToolPermissionMode[] = ["allow", "ask", "block"];

export function PermissionsSection() {
  const [state, setState] = useState<AgentControlState | null>(null);
  const [tools, setTools] = useState<AgentPermissionTool[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextState, perms] = await Promise.all([getAgentControl(), getAgentPermissions()]);
      setState(nextState);
      setTools(perms.tools);
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

  async function setToolMode(name: string, mode: ToolPermissionMode) {
    setBusy(true);
    setError(null);
    try {
      const next = await patchAgentControl({ tool_permissions: { [name]: mode } });
      setState(next);
      const perms = await getAgentPermissions();
      setTools(perms.tools);
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
            <p className="mt-1 text-sm text-[var(--muted)]">{AUTONOMY_TODAY}</p>
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
              {PRESETS.map((id) => {
                const active = state.autonomy_preset === id;
                return (
                  <li key={id}>
                    <button
                      type="button"
                      disabled={busy}
                      aria-pressed={active}
                      onClick={() => void setPreset(id)}
                      className={`w-full rounded-[var(--radius)] border px-3 py-3 text-left transition ${
                        active
                          ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                          : "border-[var(--border)] hover:bg-[var(--canvas)]"
                      }`}
                    >
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-[var(--ink)]">
                        {AUTONOMY_LABELS[id]}
                        {active ? <StatusChip tone="success">Selected</StatusChip> : null}
                        {AUTONOMY_IN_EFFECT[id] ? null : (
                          <StatusChip tone="neutral">Not active yet</StatusChip>
                        )}
                      </p>
                      <p className="mt-1 text-xs text-[var(--muted)]">{AUTONOMY_BLURBS[id]}</p>
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
                Approved commits today: {state.budgets.commits_used} of {state.budgets.commits_cap}{" "}
                · scheduled messages: {state.budgets.proactive_used} of{" "}
                {state.budgets.proactive_cap}
              </p>
            </div>
          </>
        ) : null}
      </section>

      <section className={panelClass} aria-labelledby="settings-permissions-heading">
        <h2 id="settings-permissions-heading" className="text-sm font-semibold text-[var(--ink)]">
          What always holds
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          These rules are enforced by the server for every channel.
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-[var(--ink)]">
          {BULLETS.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className={panelClass} aria-labelledby="settings-advanced-permissions">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2
              id="settings-advanced-permissions"
              className="text-sm font-semibold text-[var(--ink)]"
            >
              Advanced: per capability
            </h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Allow, Ask or Block each tool. Send and delete cannot be set to Allow.
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => setShowAdvanced((value) => !value)}
          >
            {showAdvanced ? "Hide" : "Show"}
          </Button>
        </div>
        {showAdvanced ? (
          <ul className="mt-4 flex flex-col gap-2">
            {tools.map((tool) => (
              <li
                key={tool.name}
                className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] py-2 last:border-0"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--ink)]">{tool.name}</p>
                  <p className="text-xs text-[var(--muted)]">
                    {tool.access_kind}
                    {tool.ceiling ? " · ceiling" : ""}
                  </p>
                </div>
                <div className="flex gap-1">
                  {MODES.map((mode) => {
                    const disabled = busy || (mode === "allow" && tool.ceiling);
                    return (
                      <Button
                        key={mode}
                        type="button"
                        size="sm"
                        variant={tool.mode === mode ? "primary" : "secondary"}
                        disabled={disabled}
                        onClick={() => void setToolMode(tool.name, mode)}
                      >
                        {mode}
                      </Button>
                    );
                  })}
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  );
}
