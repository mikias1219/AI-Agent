"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusChip } from "@/components/ui/status-chip";
import { apiErrorMessage } from "@/lib/api/client";
import {
  AUTONOMY_BLURBS,
  AUTONOMY_IN_EFFECT,
  AUTONOMY_LABELS,
  getAgentControl,
  patchAgentControl,
  type AgentControlState,
  type AutonomyPresetId,
} from "@/lib/api/agent-control";
import { getStatus } from "@/lib/api/status";
import type { StatusPayload } from "@/lib/api/types";

const PRESETS: AutonomyPresetId[] = ["ask_first", "balanced", "proactive"];

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-[var(--muted)]">{label}</dt>
      <dd className="mt-1 text-sm font-medium break-words text-[var(--ink)]">{value}</dd>
    </div>
  );
}

function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm text-[var(--danger)]" role="alert">
      <span>{message}</span>
      <Button size="sm" variant="secondary" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}

export function AgentSection() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [control, setControl] = useState<AgentControlState | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setStatusError(null);
    setControlError(null);
    await Promise.all([
      getStatus()
        .then(setStatus)
        .catch((err) => setStatusError(apiErrorMessage(err))),
      getAgentControl()
        .then(setControl)
        .catch((err) => setControlError(apiErrorMessage(err))),
    ]);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function patch(input: Parameters<typeof patchAgentControl>[0]) {
    setBusy(true);
    setControlError(null);
    try {
      setControl(await patchAgentControl(input));
    } catch (err) {
      setControlError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card
        id="settings-model-heading"
        title="Model"
        description="Set in the server environment, not here."
      >
        {loading ? (
          <div aria-busy="true" className="flex flex-col gap-2">
            <Skeleton className="w-1/2" />
            <Skeleton className="w-2/3" />
          </div>
        ) : statusError || !status ? (
          <LoadError
            message={statusError ?? "Could not load the model."}
            onRetry={() => void load()}
          />
        ) : (
          <>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Provider" value={status.provider} />
              <Field label="Model" value={status.model} />
            </dl>
            <p className="mt-4 text-xs text-[var(--muted)]">
              Telegram is managed under{" "}
              <Link
                href="/connections/telegram"
                className="font-medium text-[var(--accent)] hover:underline"
              >
                Connections
              </Link>
              .
            </p>
          </>
        )}
      </Card>

      <Card
        id="settings-autonomy-heading"
        title="Autonomy"
        description="How much AURA does before asking."
        action={
          control ? (
            <StatusChip tone={control.paused ? "warning" : "success"}>
              {control.paused ? "Paused" : "Listening"}
            </StatusChip>
          ) : null
        }
      >
        {loading ? (
          <div aria-busy="true" className="flex flex-col gap-2">
            <Skeleton heightClass="h-14" />
            <Skeleton heightClass="h-14" />
          </div>
        ) : controlError && !control ? (
          <LoadError message={controlError} onRetry={() => void load()} />
        ) : control ? (
          <>
            <ul className="flex flex-col gap-2">
              {PRESETS.map((id) => {
                const active = control.autonomy_preset === id;
                const live = AUTONOMY_IN_EFFECT[id];
                return (
                  <li key={id}>
                    <button
                      type="button"
                      disabled={busy}
                      aria-pressed={active}
                      onClick={() => void patch({ autonomy_preset: id })}
                      className={`min-h-11 w-full rounded-[var(--radius)] border px-3 py-3 text-left transition ${
                        active
                          ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                          : "border-[var(--border)] hover:bg-[var(--canvas)]"
                      }`}
                    >
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-[var(--ink)]">
                        {AUTONOMY_LABELS[id]}
                        {active ? <StatusChip tone="accent">Selected</StatusChip> : null}
                        {live ? null : <StatusChip>Saved, not enforced yet</StatusChip>}
                      </p>
                      <p className="mt-1 text-xs text-[var(--muted)]">{AUTONOMY_BLURBS[id]}</p>
                    </button>
                  </li>
                );
              })}
            </ul>
            {controlError ? (
              <p className="mt-3 text-sm text-[var(--danger)]" role="alert">
                {controlError}
              </p>
            ) : null}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="secondary"
                loading={busy}
                onClick={() => void patch({ paused: !control.paused })}
              >
                {control.paused ? "Resume agent" : "Pause agent"}
              </Button>
              <p className="text-xs text-[var(--muted)]">
                Approved today: {control.budgets.commits_used} of {control.budgets.commits_cap}
              </p>
            </div>
          </>
        ) : null}
      </Card>
    </div>
  );
}
