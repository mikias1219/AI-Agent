"use client";

import { FormEvent, useState } from "react";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/lib/api/client";
import { forgetAllMemories, issueForgetToken } from "@/lib/api/memories";
import { exportWorkspace, issueWipeToken, wipeWorkspace } from "@/lib/api/workspace";

const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

export function DataSection() {
  const [token, setToken] = useState<string | null>(null);
  const [phrase, setPhrase] = useState("");
  const [wipeToken, setWipeToken] = useState<string | null>(null);
  const [wipePhrase, setWipePhrase] = useState("");
  const [busy, setBusy] = useState<"forget" | "wipe" | "export" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function downloadExport() {
    setBusy("export");
    setError(null);
    setMessage(null);
    try {
      const payload = await exportWorkspace();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `aura-export-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("Export downloaded.");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function requestToken() {
    setBusy("forget");
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
      setBusy(null);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setBusy("forget");
    setError(null);
    try {
      const result = await forgetAllMemories({ token, confirm_phrase: phrase });
      setToken(null);
      setPhrase("");
      setMessage(`Deleted ${result.deleted} ${result.deleted === 1 ? "memory" : "memories"}.`);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function requestWipe() {
    setBusy("wipe");
    setError(null);
    setMessage(null);
    try {
      const issued = await issueWipeToken();
      setWipeToken(issued.token);
      setWipePhrase("");
      setMessage(
        `Type ${issued.confirm_phrase} to wipe tasks, memories, open suggestions, mark goals done, and disconnect Google.`,
      );
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function onWipe(event: FormEvent) {
    event.preventDefault();
    if (!wipeToken) return;
    setBusy("wipe");
    setError(null);
    try {
      const result = await wipeWorkspace({ token: wipeToken, confirm_phrase: wipePhrase });
      setWipeToken(null);
      setWipePhrase("");
      const parts = Object.entries(result.deleted)
        .map(([key, value]) => `${value} ${key}`)
        .join(", ");
      setMessage(
        `Workspace wiped (${parts})${result.google_cleared ? "; Google disconnected" : ""}.`,
      );
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className={panelClass} aria-labelledby="settings-data-heading">
      <h2 id="settings-data-heading" className="text-sm font-semibold text-[var(--ink)]">
        Data
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Export a JSON copy of your workspace, forget memories, or wipe the workspace. Wipes cannot
        be undone.
      </p>

      <div className="mt-4 flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-medium text-[var(--ink)]">Export</h3>
          <Button
            variant="secondary"
            disabled={busy !== null}
            loading={busy === "export"}
            onClick={() => void downloadExport()}
          >
            Download my data
          </Button>
        </div>

        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-medium text-[var(--ink)]">Forget memories</h3>
          <Button variant="secondary" disabled={busy !== null} onClick={() => void requestToken()}>
            {busy === "forget" && !token ? "Preparing…" : "Forget everything…"}
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
              <Button type="submit" disabled={busy !== null || phrase.trim().length === 0}>
                {busy === "forget" ? "Deleting…" : "Delete all memories"}
              </Button>
            </form>
          ) : null}
        </div>

        <div className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--danger)]/40 p-3">
          <h3 className="text-sm font-medium text-[var(--ink)]">Wipe workspace</h3>
          <p className="text-xs text-[var(--muted)]">
            Soft-deletes tasks, forgets memories, dismisses open suggestions, marks goals done, and
            disconnects Google. Your login stays so you can start again.
          </p>
          <Button variant="secondary" disabled={busy !== null} onClick={() => void requestWipe()}>
            {busy === "wipe" && !wipeToken ? "Preparing…" : "Wipe workspace…"}
          </Button>
          {wipeToken ? (
            <form onSubmit={onWipe} className="flex flex-col gap-3">
              <Field label='Type "WIPE WORKSPACE" to confirm' htmlFor="wipe-phrase">
                <Input
                  id="wipe-phrase"
                  value={wipePhrase}
                  onChange={(e) => setWipePhrase(e.target.value)}
                  autoComplete="off"
                />
              </Field>
              <Button type="submit" disabled={busy !== null || wipePhrase.trim().length === 0}>
                {busy === "wipe" ? "Wiping…" : "Wipe workspace"}
              </Button>
            </form>
          ) : null}
        </div>

        {message ? <Banner tone="success">{message}</Banner> : null}
        {error ? (
          <Banner tone="danger" role="alert">
            {error}
          </Banner>
        ) : null}
      </div>
    </section>
  );
}
