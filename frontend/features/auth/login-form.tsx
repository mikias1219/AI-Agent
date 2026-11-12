"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordField } from "./password-field";
import { authErrorMessage, useAuth } from "./use-auth";

export type LoginFormProps = {
  successNote?: string | null;
};

export function LoginForm({ successNote }: LoginFormProps) {
  const router = useRouter();
  const { status, loading: authLoading, login } = useAuth();
  const emailRequired = status?.email_required ?? true;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const next: { email?: string; password?: string } = {};
    const trimmedEmail = email.trim();
    if (emailRequired && !trimmedEmail) {
      next.email = "Email is required.";
    }
    if (!password) {
      next.password = "Password is required.";
    }
    setFieldErrors(next);
    if (Object.keys(next).length > 0) {
      return;
    }

    setFormError(null);
    setSubmitting(true);
    try {
      await login(emailRequired ? trimmedEmail : null, password);
      router.replace("/");
    } catch (err) {
      setFormError(authErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  const disabled = authLoading || submitting;

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-col gap-4">
      {successNote ? (
        <p
          className="rounded-[var(--radius)] border border-[var(--success)]/30 bg-[color-mix(in_srgb,var(--success)_8%,var(--surface))] px-3 py-2 text-sm text-[var(--success)]"
          role="status"
        >
          {successNote}
        </p>
      ) : null}

      {formError ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {formError}
        </p>
      ) : null}

      {emailRequired ? (
        <Field label="Email" htmlFor="login-email" error={fieldErrors.email}>
          <Input
            id="login-email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={disabled}
          />
        </Field>
      ) : null}

      <PasswordField
        label="Password"
        value={password}
        onChange={setPassword}
        error={fieldErrors.password}
        disabled={disabled}
      />

      <Button type="submit" loading={submitting} disabled={disabled} className="w-full">
        Sign in
      </Button>

      <p className="text-center text-sm text-[var(--muted)]">
        {status?.registered === false ? (
          <>
            No account yet?{" "}
            <Link href="/register" className="font-medium text-[var(--accent)] hover:underline">
              Create one
            </Link>
          </>
        ) : (
          <>
            Need an account?{" "}
            <Link href="/register" className="font-medium text-[var(--accent)] hover:underline">
              Register
            </Link>
          </>
        )}
      </p>
      <p className="text-center text-sm text-[var(--muted)]">
        Or{" "}
        <Link href="/demo" className="font-medium text-[var(--accent)] hover:underline">
          try the demo
        </Link>{" "}
        without signing in.
      </p>
    </form>
  );
}
