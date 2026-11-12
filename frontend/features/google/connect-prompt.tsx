"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, buttonClassName } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { apiErrorMessage } from "@/lib/api/client";
import { connectGoogle, type GoogleStatus } from "@/lib/api/google";

export type ConnectPromptProps = {
  /** What the connected account is for on this screen, e.g. "events" or "mail". */
  noun: string;
  status: GoogleStatus | null;
};

/** Honest disconnected state: no sample rows, only a way to connect. */
export function ConnectPrompt({ noun, status }: ConnectPromptProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const configured = status?.oauth_configured !== false;

  async function onConnect() {
    setBusy(true);
    setError(null);
    try {
      const res = await connectGoogle();
      if (res.auth_url) window.location.assign(res.auth_url);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div data-testid="google-disconnected" className="flex flex-col gap-3">
      <EmptyState
        title="Google is not connected"
        description={
          configured
            ? `Connect Google and AURA will show your ${noun} here. Until then, nothing is shown.`
            : `Google sign-in is not set up on this server yet, so no ${noun} can be shown. Add the Google client ID and secret under Connections.`
        }
        action={
          configured ? (
            <Button type="button" loading={busy} onClick={() => void onConnect()}>
              Connect Google
            </Button>
          ) : (
            <Link href="/connections/google" className={buttonClassName("secondary")}>
              Open Google connection
            </Link>
          )
        }
      />
      {error ? (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {error}
        </p>
      ) : null}
    </div>
  );
}
