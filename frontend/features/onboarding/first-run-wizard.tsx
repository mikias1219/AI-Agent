"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/lib/api/client";
import { AUTONOMY_LABELS, patchAgentControl, type AutonomyPresetId } from "@/lib/api/agent-control";
import { completeWizard, type OnboardingState } from "@/lib/api/onboarding";

const PRESET_OPTIONS: { id: AutonomyPresetId; blurb: string }[] = [
  { id: "ask_first", blurb: "Ask before changes. Best while you learn AURA." },
  { id: "balanced", blurb: "Read freely; ask before important commits." },
  { id: "proactive", blurb: "May notify within quiet hours and the daily cap." },
];

export function FirstRunWizard({ onCompleted }: { onCompleted: (state: OnboardingState) => void }) {
  const [step, setStep] = useState<"profile" | "autonomy">("profile");
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [preset, setPreset] = useState<AutonomyPresetId>("ask_first");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onProfile(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setStep("autonomy");
  }

  async function onFinish(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await patchAgentControl({ autonomy_preset: preset }).catch(() => {
        /* profile can still complete if control patch fails */
      });
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

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-5 py-8">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">First run</p>
        <h1
          className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {step === "profile" ? "Set up AURA" : "Choose autonomy"}
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          {step === "profile"
            ? "Name and timezone so dates and greetings match how you work."
            : "Hard ceilings (new recipients, delete, spending, sharing) always need approval."}
        </p>
      </header>

      {step === "profile" ? (
        <form
          onSubmit={onProfile}
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
      ) : (
        <form
          onSubmit={onFinish}
          className="flex flex-col gap-4 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5"
        >
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
            <Button
              type="button"
              variant="secondary"
              disabled={busy}
              onClick={() => setStep("profile")}
            >
              Back
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Saving…" : "Continue to Today"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
