"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button, buttonClassName } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/lib/api/client";
import {
  AUTONOMY_BLURBS,
  AUTONOMY_IN_EFFECT,
  AUTONOMY_LABELS,
  patchAgentControl,
  type AutonomyPresetId,
} from "@/lib/api/agent-control";
import { getGoogleStatus } from "@/lib/api/google";
import { completeWizard, type OnboardingState } from "@/lib/api/onboarding";

type Step = "profile" | "connect" | "autonomy" | "ready";

const STEPS: { id: Step; label: string }[] = [
  { id: "profile", label: "About you" },
  { id: "connect", label: "Connect" },
  { id: "autonomy", label: "Autonomy" },
  { id: "ready", label: "Ready" },
];

const PRESET_OPTIONS: AutonomyPresetId[] = ["ask_first", "balanced", "proactive"];

const cardClass =
  "flex flex-col gap-4 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5";

export function FirstRunWizard({ onCompleted }: { onCompleted: (state: OnboardingState) => void }) {
  const [step, setStep] = useState<Step>("profile");
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [preset, setPreset] = useState<AutonomyPresetId>("ask_first");
  const [googleConnected, setGoogleConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getGoogleStatus()
      .then((s) => setGoogleConnected(Boolean(s.connected)))
      .catch(() => setGoogleConnected(false));
  }, []);

  function go(next: Step) {
    setError(null);
    setStep(next);
  }

  async function finish(useChoices: boolean) {
    setBusy(true);
    setError(null);
    try {
      if (useChoices) {
        await patchAgentControl({ autonomy_preset: preset }).catch(() => undefined);
      }
      const state = await completeWizard({
        name: useChoices ? name.trim() || undefined : undefined,
        timezone: (useChoices ? timezone.trim() : "") || "UTC",
      });
      onCompleted(state);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const stepIndex = STEPS.findIndex((s) => s.id === step);
  const errorNote = error ? (
    <p className="text-sm text-[var(--danger)]" role="alert">
      {error}
    </p>
  ) : null;

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-5 py-6">
      <header className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <h1
            className="text-xl font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Set up AURA
          </h1>
          <Button
            type="button"
            variant="ghost"
            className="min-h-11"
            disabled={busy}
            onClick={() => void finish(false)}
          >
            Skip setup
          </Button>
        </div>
        <div
          role="progressbar"
          aria-label="Setup progress"
          aria-valuemin={1}
          aria-valuemax={STEPS.length}
          aria-valuenow={stepIndex + 1}
          aria-valuetext={`Step ${stepIndex + 1} of ${STEPS.length}: ${STEPS[stepIndex]?.label}`}
          className="flex gap-1.5"
        >
          {STEPS.map((item, index) => (
            <span
              key={item.id}
              aria-hidden
              className={`h-1.5 flex-1 rounded-full ${
                index <= stepIndex ? "bg-[var(--accent)]" : "bg-[var(--border)]"
              }`}
            />
          ))}
        </div>
        <p className="text-xs text-[var(--muted)]">
          Step {stepIndex + 1} of {STEPS.length} · {STEPS[stepIndex]?.label}
        </p>
      </header>

      {step === "profile" ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            go("connect");
          }}
          className={cardClass}
        >
          <h2 className="text-sm font-semibold text-[var(--ink)]">What should AURA call you?</h2>
          <Field label="Your name" htmlFor="wizard-name">
            <Input
              id="wizard-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Optional"
            />
          </Field>
          <Field label="Timezone" htmlFor="wizard-timezone">
            <Input
              id="wizard-timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              required
            />
          </Field>
          <Button type="submit" className="min-h-11">
            Continue
          </Button>
        </form>
      ) : null}

      {step === "connect" ? (
        <div className={cardClass}>
          <h2 className="text-sm font-semibold text-[var(--ink)]">Connect Google (optional)</h2>
          <p className="text-sm text-[var(--muted)]">
            Lets AURA read your calendar and mail. You can do this later.
          </p>
          <p className="text-sm text-[var(--ink)]">
            Google: {googleConnected ? "Connected" : "Not connected"}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              className="min-h-11"
              onClick={() => go("profile")}
            >
              Back
            </Button>
            {googleConnected ? null : (
              <Link href="/connections" className={buttonClassName("secondary", "md", "min-h-11")}>
                Open Connections
              </Link>
            )}
            <Button type="button" className="min-h-11" onClick={() => go("autonomy")}>
              {googleConnected ? "Continue" : "Skip for now"}
            </Button>
          </div>
        </div>
      ) : null}

      {step === "autonomy" ? (
        <div className={cardClass}>
          <h2 className="text-sm font-semibold text-[var(--ink)]">
            How much should AURA do on its own?
          </h2>
          <p className="text-sm text-[var(--muted)]">You can change this any time in Settings.</p>
          <ul className="flex flex-col gap-2">
            {PRESET_OPTIONS.map((id) => {
              const active = preset === id;
              return (
                <li key={id}>
                  <button
                    type="button"
                    aria-pressed={active}
                    onClick={() => setPreset(id)}
                    className={`min-h-11 w-full rounded-[var(--radius)] border px-3 py-3 text-left ${
                      active
                        ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                        : "border-[var(--border)] hover:bg-[var(--canvas)]"
                    }`}
                  >
                    <p className="text-sm font-medium text-[var(--ink)]">
                      {AUTONOMY_LABELS[id]}
                      {id === "ask_first" ? " · Recommended" : ""}
                      {AUTONOMY_IN_EFFECT[id] ? "" : " · Saved, not enforced yet"}
                    </p>
                    <p className="mt-1 text-xs text-[var(--muted)]">{AUTONOMY_BLURBS[id]}</p>
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              className="min-h-11"
              onClick={() => go("connect")}
            >
              Back
            </Button>
            <Button type="button" className="min-h-11" onClick={() => go("ready")}>
              Continue
            </Button>
          </div>
        </div>
      ) : null}

      {step === "ready" ? (
        <div className={cardClass}>
          <h2 className="text-sm font-semibold text-[var(--ink)]">You are ready</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            <li>Name: {name.trim() || "not set"}</li>
            <li>Timezone: {timezone.trim() || "UTC"}</li>
            <li>Google: {googleConnected ? "connected" : "not connected"}</li>
            <li>Autonomy: {AUTONOMY_LABELS[preset]}</li>
          </ul>
          {errorNote}
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              className="min-h-11"
              disabled={busy}
              onClick={() => go("autonomy")}
            >
              Back
            </Button>
            <Button
              type="button"
              className="min-h-11"
              loading={busy}
              onClick={() => void finish(true)}
            >
              Finish setup
            </Button>
          </div>
        </div>
      ) : null}
      {step !== "ready" ? errorNote : null}
    </div>
  );
}
