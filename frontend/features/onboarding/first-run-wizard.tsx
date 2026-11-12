"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/lib/api/client";
import { completeWizard, type OnboardingState } from "@/lib/api/onboarding";

export function FirstRunWizard({ onCompleted }: { onCompleted: (state: OnboardingState) => void }) {
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
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
          Set up AURA
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Name and timezone so dates and greetings match how you work. You can change these later in
          Settings.
        </p>
      </header>
      <form
        onSubmit={onSubmit}
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
        {error ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : "Continue to Today"}
        </Button>
      </form>
    </div>
  );
}
