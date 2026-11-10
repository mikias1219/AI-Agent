"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import { PasswordField } from "./password-field";
import { authErrorMessage, useAuth } from "./use-auth";

export function RegisterForm() {
  const router = useRouter();
  const { loading: authLoading, register } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string;
    email?: string;
    password?: string;
  }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [registrationClosed, setRegistrationClosed] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const next: { name?: string; email?: string; password?: string } = {};
    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    if (!trimmedName) {
      next.name = "Name is required.";
    }
    if (!trimmedEmail) {
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
    setRegistrationClosed(false);
    setSubmitting(true);
    try {
      await register(trimmedName, trimmedEmail, password);
      router.replace("/login?registered=1");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setRegistrationClosed(true);
        setFormError(null);
      } else {
        setFormError(authErrorMessage(err));
      }
    } finally {
      setSubmitting(false);
    }
  }

  const disabled = authLoading || submitting;

  if (registrationClosed) {
    return (
      <div className="flex w-full flex-col gap-4 text-center">
        <p className="text-sm text-[var(--ink)]">Registration is closed</p>
        <p className="text-sm text-[var(--muted)]">
          An owner account already exists for this workspace.
        </p>
        <Link href="/login" className="text-sm font-medium text-[var(--accent)] hover:underline">
          Sign in instead
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-col gap-4">
      {formError ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {formError}
        </p>
      ) : null}

      <Field label="Name" htmlFor="register-name" error={fieldErrors.name}>
        <Input
          id="register-name"
          name="name"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={disabled}
        />
      </Field>

      <Field label="Email" htmlFor="register-email" error={fieldErrors.email}>
        <Input
          id="register-email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={disabled}
        />
      </Field>

      <PasswordField
        label="Password"
        value={password}
        onChange={setPassword}
        error={fieldErrors.password}
        autoComplete="new-password"
        disabled={disabled}
      />

      <Button type="submit" loading={submitting} disabled={disabled} className="w-full">
        Create account
      </Button>

      <p className="text-center text-sm text-[var(--muted)]">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-[var(--accent)] hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
