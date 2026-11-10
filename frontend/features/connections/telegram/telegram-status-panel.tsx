"use client";

import { Play, ShieldCheck, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { TelegramIdentity } from "@/lib/api/telegram";
import type { TelegramStatusPayload } from "@/lib/api/types";
import { formatWhen, runtimeLabel } from "../format";

const FOREIGN_RUNTIME = ["starting", "polling", "responding", "error"];

export type TelegramStatusPanelProps = {
  status: TelegramStatusPayload;
  identity: TelegramIdentity | null;
  busy: "verify" | "start" | "stop" | null;
  stopping: boolean;
  actionError: string | null;
  notice: string | null;
  onVerify: () => void;
  onStart: () => void;
  onStop: () => void;
};

export function TelegramStatusPanel({
  status,
  identity,
  busy,
  stopping,
  actionError,
  notice,
  onVerify,
  onStart,
  onStop,
}: TelegramStatusPanelProps) {
  const username = identity?.username || status.username;
  const managed = status.managed;
  const foreign = !managed && FOREIGN_RUNTIME.includes(status.runtime);
  const showStop = managed || stopping;
  const phase = stopping && managed ? "Stopping…" : runtimeLabel(status.runtime);
  const allowed =
    status.allowed_chat_ids.length > 0
      ? status.allowed_chat_ids.join(", ")
      : "None — replies stay blocked";

  return (
    <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-[var(--ink)]">
            {username ? `@${username}` : "Telegram bot"}
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]" role="status">
            {phase}
          </p>
        </div>
        <ShieldCheck className="h-5 w-5 text-[var(--success)]" aria-hidden />
      </div>

      <dl className="mt-5 space-y-3 text-sm">
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Bot token</dt>
          <dd className="text-right text-[var(--ink)]">
            {status.configured ? "Configured · hidden" : "Not configured"}
          </dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Managed here</dt>
          <dd className="text-right text-[var(--ink)]">{managed ? "Yes" : "No"}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Allowed chats</dt>
          <dd className="max-w-[16rem] text-right break-words text-[var(--ink)]">{allowed}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Last heartbeat</dt>
          <dd className="text-right text-[var(--ink)]">
            {status.last_seen ? formatWhen(status.last_seen) : "Not seen"}
          </dd>
        </div>
      </dl>

      {!status.configured ? (
        <p className="mt-4 text-sm text-[var(--muted)]">
          Add <code className="text-[var(--ink)]">TELEGRAM_BOT_TOKEN</code> to{" "}
          <code className="text-[var(--ink)]">backend/.env</code> and restart the backend.
        </p>
      ) : null}

      {foreign ? (
        <p className="mt-4 text-sm text-[var(--muted)]">
          A bot looks active in another process ({runtimeLabel(status.runtime)}). Stop that process
          before starting one here. Command:{" "}
          <code className="text-[var(--ink)]">{status.command}</code>.
        </p>
      ) : null}

      {status.error_type && status.runtime === "error" ? (
        <p className="mt-4 text-sm text-[var(--danger)]" role="alert">
          Last error: {status.error_type}. Check the token and the backend logs.
        </p>
      ) : null}

      {notice ? (
        <p className="mt-4 text-sm text-[var(--ink)]" role="status">
          {notice}
        </p>
      ) : null}
      {actionError ? (
        <p className="mt-4 text-sm text-[var(--danger)]" role="alert">
          {actionError}
        </p>
      ) : null}

      <div className="mt-5 flex flex-wrap gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={!status.configured || busy !== null}
          loading={busy === "verify"}
          onClick={onVerify}
        >
          Verify identity
        </Button>
        {showStop ? (
          <Button
            variant="secondary"
            size="sm"
            disabled={busy !== null || stopping}
            loading={busy === "stop"}
            onClick={onStop}
          >
            <Square className="h-3.5 w-3.5" aria-hidden />
            Stop bot
          </Button>
        ) : (
          <Button
            size="sm"
            disabled={!status.configured || foreign || busy !== null}
            loading={busy === "start"}
            onClick={onStart}
          >
            <Play className="h-3.5 w-3.5" aria-hidden />
            Start bot
          </Button>
        )}
      </div>
      <p className="mt-4 text-xs leading-5 text-[var(--muted)]">
        Only allowed chats receive replies. An empty allowlist records incoming chat IDs in activity
        and does not reply.
      </p>
    </section>
  );
}
