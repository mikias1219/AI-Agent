"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { Button, buttonClassName } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/lib/api/client";
import { AUTONOMY_LABELS, patchAgentControl, type AutonomyPresetId } from "@/lib/api/agent-control";
import { getStatus } from "@/lib/api/status";
import { getGoogleStatus } from "@/lib/api/google";
import { completeWizard, type OnboardingState } from "@/lib/api/onboarding";

type Step = "profile" | "model" | "connect" | "autonomy";

const STEPS: { id: Step; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "model", label: "Model" },
  { id: "connect", label: "Connect" },
  { id: "autonomy", label: "Autonomy" },
];

const PRESET_OPTIONS: { id: AutonomyPresetId; blurb: string }[] = [
  { id: "ask_first", blurb: "Everything that sends or changes something waits for your OK." },
  {
    id: "balanced",
    blurb: "Familiar actions may proceed with clear receipts; hard ceilings still ask.",
  },
  {
    id: "proactive",
    blurb:
      "Routine low-risk actions may run, then AURA tells you — within quiet hours and the daily cap.",
  },
];

export function FirstRunWizard({ onCompleted }: { onCompleted: (state: OnboardingState) => void }) {
  const [step, setStep] = useState<Step>("profile");
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [preset, setPreset] = useState<AutonomyPresetId>("ask_first");
  const [providerLabel, setProviderLabel] = useState<string | null>(null);
  const [googleConnected, setGoogleConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStatus()
      .then((status) => {
        const provider = typeof status.provider === "string" ? status.provider : "unknown";
        const model = typeof status.model === "string" ? status.model : "";
        setProviderLabel(model ? `${provider} · ${model}` : provider);
      })
      .catch(() => setProviderLabel("Unavailable right now"));
    getGoogleStatus()
      .then((s) => setGoogleConnected(Boolean(s.connected)))
      .catch(() => setGoogleConnected(false));
  }, []);

  function go(next: Step) {
    setError(null);
    setStep(next);
  }

  async function onFinish(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await patchAgentControl({ autonomy_preset: preset }).catch(() => undefined);
      const state = await completeWizard({
        name: name.trim() || undefined,
        timezone: timezone.trim() || "UTC",
      });
      onCompleted(state);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const stepIndex = STEPS.findIndex((s) => s.id === step);

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-5 py-8">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Welcome</p>
        <h1
          className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          AURA
        </h1>
        <ol className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--muted)]">
          {STEPS.map((item, index) => (
            <li
              key={item.id}
              className={index === stepIndex ? "font-semibold text-[var(--accent)]" : undefined}
            >
              {index + 1} {item.label}
            </li>
          ))}
        </ol>
      </header>

      {step === "profile" ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            go("model");
          }}
          className="flex flex-col gap-4 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5"
        >
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
          <Button type="submit">Continue</Button>
        </form>
      ) : null}

      {step === "model" ? (
        <div className="flex flex-col gap-4 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5">
          <h2 className="text-sm font-semibold text-[var(--ink)]">Model</h2>
          <p className="text-sm text-[var(--muted)]">
            AURA uses the provider configured on this server. This step is read-only honesty — no
            invented models.
          </p>
          <p className="rounded-md border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm text-[var(--ink)]">
            {providerLabel ?? "Loading…"}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => go("profile")}>
              Back
            </Button>
            <Button type="button" onClick={() => go("connect")}>
              Continue
            </Button>
          </div>
        </div>
      ) : null}

      {step === "connect" ? (
        <div className="flex flex-col gap-4 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5">
          <h2 className="text-sm font-semibold text-[var(--ink)]">Connect</h2>
          <p className="text-sm text-[var(--muted)]">
            Optional. Connect Google for calendar and mail. You can skip and do this later.
          </p>
          <p className="text-sm text-[var(--ink)]">
            Google: {googleConnected ? "Connected" : "Not connected"}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => go("model")}>
              Back
            </Button>
            <Link href="/connections" className={buttonClassName("secondary")}>
              Open Connections
            </Link>
            <Button type="button" onClick={() => go("autonomy")}>
              {googleConnected ? "Continue" : "Skip for now"}
            </Button>
          </div>
        </div>
      ) : null}

      {step === "autonomy" ? (
        <form
          onSubmit={onFinish}
          className="flex flex-col gap-4 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5"
        >
          <h2 className="text-sm font-semibold text-[var(--ink)]">
            How much should AURA do on its own?
          </h2>
          <p className="text-sm text-[var(--muted)]">
            You can change this any time from the header. Hard ceilings always need approval.
          </p>
          <ul className="flex flex-col gap-2">
            {PRESET_OPTIONS.map((option) => {
              const active = preset === option.id;
              return (
                <li key={option.id}>
                  <button
                    type="button"
                    onClick={() => setPreset(option.id)}
                    className={`w-full rounded-[var(--radius)] border px-3 py-3 text-left ${
                      active
                        ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                        : "border-[var(--border)] hover:bg-[var(--canvas)]"
                    }`}
                  >
                    <p className="text-sm font-medium text-[var(--ink)]">
                      {AUTONOMY_LABELS[option.id]}
                      {option.id === "ask_first" ? " · Recommended" : ""}
                    </p>
                    <p className="mt-1 text-xs text-[var(--muted)]">{option.blurb}</p>
                  </button>
                </li>
              );
            })}
          </ul>
          {error ? (
            <p className="text-sm text-[var(--danger)]" role="alert">
              {error}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" disabled={busy} onClick={() => go("connect")}>
              Back
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Saving…" : "Finish setup"}
            </Button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
