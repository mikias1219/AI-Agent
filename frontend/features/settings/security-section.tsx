"use client";

import { useState, type FormEvent } from "react";
import { Eye, EyeOff } from "lucide-react";
import { ApiError, apiErrorMessage } from "@/lib/api/client";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { changePassword, MIN_PASSWORD_LENGTH, passwordStrength } from "@/lib/api/profile";

const STRENGTH_BAR = [
  "bg-[var(--danger)]",
  "bg-[var(--warning)]",
  "bg-[var(--info)]",
  "bg-[var(--success)]",
];

type Errors = { current?: string; next?: string; confirm?: string; form?: string };

export function SecuritySection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const strength = passwordStrength(next);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const found: Errors = {};
    if (!current) found.current = "Enter your current password.";
    if (next.length < MIN_PASSWORD_LENGTH) {
      found.next = `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
    } else if (next === current) {
      found.next = "Choose a password different from your current one.";
    }
    if (confirm !== next) found.confirm = "The two passwords do not match.";
    setErrors(found);
    setDone(false);
    if (Object.keys(found).length > 0) return;
    setBusy(true);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setErrors({ current: "That is not your current password. Check it and try again." });
      } else if (err instanceof ApiError && err.status === 400) {
        setErrors({ next: err.message });
      } else if (err instanceof ApiError && err.status === 429) {
        setErrors({ form: "Too many attempts. Wait a minute and try again." });
      } else {
        setErrors({ form: apiErrorMessage(err) });
      }
    } finally {
      setBusy(false);
    }
  }

  const type = show ? "text" : "password";

  return (
    <Card
      title="Change password"
      description="Use at least 12 characters. A short phrase of random words works well."
    >
      <form className="flex max-w-md flex-col gap-4" noValidate onSubmit={(e) => void onSubmit(e)}>
        {done ? (
          <Banner tone="success" role="status">
            Password changed. Your other devices were signed out.
          </Banner>
        ) : null}
        <Field label="Current password" htmlFor="pw-current" error={errors.current}>
          <Input
            id="pw-current"
            type={type}
            autoComplete="current-password"
            value={current}
            onChange={(e) => {
              setCurrent(e.target.value);
              setErrors((p) => ({ ...p, current: undefined }));
            }}
          />
        </Field>
        <Field label="New password" htmlFor="pw-new" error={errors.next}>
          <Input
            id="pw-new"
            type={type}
            autoComplete="new-password"
            value={next}
            aria-describedby="pw-strength"
            onChange={(e) => {
              setNext(e.target.value);
              setErrors((p) => ({ ...p, next: undefined }));
            }}
          />
          <div id="pw-strength" aria-live="polite" className="min-h-[2.25rem]">
            {next ? (
              <>
                <div className="flex gap-1" aria-hidden>
                  {[0, 1, 2, 3].map((i) => (
                    <span
                      key={i}
                      className={`h-1 flex-1 rounded-full ${
                        next.length >= MIN_PASSWORD_LENGTH && i <= strength.score
                          ? STRENGTH_BAR[strength.score]
                          : i === 0 && next.length < MIN_PASSWORD_LENGTH
                            ? STRENGTH_BAR[0]
                            : "bg-[var(--border)]"
                      }`}
                    />
                  ))}
                </div>
                <p className="mt-1 text-[length:var(--text-caption)] text-[var(--muted)]">
                  {strength.label}
                </p>
              </>
            ) : null}
          </div>
        </Field>
        <Field label="Confirm new password" htmlFor="pw-confirm" error={errors.confirm}>
          <Input
            id="pw-confirm"
            type={type}
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => {
              setConfirm(e.target.value);
              setErrors((p) => ({ ...p, confirm: undefined }));
            }}
          />
        </Field>
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          aria-pressed={show}
          className="inline-flex min-h-[44px] w-fit items-center gap-2 text-sm text-[var(--muted)] hover:text-[var(--ink)]"
        >
          {show ? (
            <EyeOff className="h-4 w-4" aria-hidden />
          ) : (
            <Eye className="h-4 w-4" aria-hidden />
          )}
          {show ? "Hide passwords" : "Show passwords"}
        </button>
        {errors.form ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {errors.form}
          </p>
        ) : null}
        <div>
          <Button type="submit" loading={busy} disabled={!current || !next || !confirm}>
            Change password
          </Button>
        </div>
      </form>
    </Card>
  );
}
