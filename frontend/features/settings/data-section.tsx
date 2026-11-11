"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/lib/api/client";
import { forgetAllMemories, issueForgetToken } from "@/lib/api/memories";

const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

export function DataSection() {
  const [token, setToken] = useState<string | null>(null);
  const [phrase, setPhrase] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function requestToken() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const issued = await issueForgetToken();
      setToken(issued.token);
      setPhrase("");
      setMessage(`Type ${issued.confirm_phrase} below to permanently delete every memory.`);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const result = await forgetAllMemories({ token, confirm_phrase: phrase });
      setToken(null);
      setPhrase("");
      setMessage(`Deleted ${result.deleted} ${result.deleted === 1 ? "memory" : "memories"}.`);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={panelClass} aria-labelledby="settings-data-heading">
      <h2 id="settings-data-heading" className="text-sm font-semibold text-[var(--ink)]">
        Data
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Forget everything removes every memory for this workspace. This cannot be undone.
      </p>
      <div className="mt-4 flex flex-col gap-3">
        <Button variant="secondary" disabled={busy} onClick={() => void requestToken()}>
          {busy && !token ? "Preparing…" : "Forget everything…"}
        </Button>
        {token ? (
          <form onSubmit={onSubmit} className="flex flex-col gap-3">
            <Field label='Type "FORGET EVERYTHING" to confirm' htmlFor="forget-phrase">
              <Input
                id="forget-phrase"
                value={phrase}
                onChange={(e) => setPhrase(e.target.value)}
                autoComplete="off"
              />
            </Field>
            <Button type="submit" disabled={busy || phrase.trim().length === 0}>
              {busy ? "Deleting…" : "Delete all memories"}
            </Button>
          </form>
        ) : null}
        {message ? <p className="text-sm text-[var(--muted)]">{message}</p> : null}
        {error ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
