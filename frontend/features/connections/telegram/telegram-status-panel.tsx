"use client";

import { Radio } from "lucide-react";
import type { TelegramStatusPayload } from "@/lib/api/types";
import { formatWhen, runtimeLabel } from "../format";

const ACTING_RUNTIMES = new Set(["starting", "polling", "responding", "running"]);

function isConnected(status: TelegramStatusPayload): boolean {
  return status.configured && status.allowed_chat_ids.length > 0;
}

function isActingAsYou(status: TelegramStatusPayload): boolean {
  return status.managed && ACTING_RUNTIMES.has(status.runtime);
}

export type TelegramStatusPanelProps = {
  status: TelegramStatusPayload;
};

export function TelegramStatusPanel({ status }: TelegramStatusPanelProps) {
  const username = status.username;
  const connected = isConnected(status);
  const acting = isActingAsYou(status);
  const headline = connected ? "Connected" : "Not connected";
  const subline = acting
    ? "Acting as you"
    : connected
      ? runtimeLabel(status.runtime)
      : "Finish setup in backend/.env";
  const allowed =
    status.allowed_chat_ids.length > 0
      ? status.allowed_chat_ids.join(", ")
      : "None — add TELEGRAM_ALLOWED_CHAT_IDS";

  return (
    <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-[var(--ink)]">
            {username ? `@${username}` : headline}
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]" role="status">
            {username ? `${headline} · ${subline}` : subline}
          </p>
        </div>
        <Radio
          className={`h-5 w-5 ${connected ? "text-[var(--success)]" : "text-[var(--muted)]"}`}
          aria-hidden
        />
      </div>

      <dl className="mt-5 space-y-3 text-sm">
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Bot token</dt>
          <dd className="text-right text-[var(--ink)]">
            {status.configured ? "Configured · hidden" : "Not configured"}
          </dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Allowlist</dt>
          <dd className="text-right text-[var(--ink)]">
            {status.allowed_chat_ids.length > 0 ? "Present" : "Missing"}
          </dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Allowed chats</dt>
          <dd className="max-w-[16rem] text-right break-words text-[var(--ink)]">{allowed}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Runtime</dt>
          <dd className="text-right text-[var(--ink)]">{runtimeLabel(status.runtime)}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-[var(--muted)]">Last seen</dt>
          <dd className="text-right text-[var(--ink)]">
            {status.last_seen ? formatWhen(status.last_seen) : "Not seen"}
          </dd>
        </div>
      </dl>

      {!status.configured ? (
        <p className="mt-4 text-sm text-[var(--muted)]">
          Add <code className="text-[var(--ink)]">TELEGRAM_BOT_TOKEN</code> to{" "}
          <code className="text-[var(--ink)]">backend/.env</code> and restart the backend. The bot
          starts automatically when an allowlist is present.
        </p>
      ) : null}

      {status.configured && status.allowed_chat_ids.length === 0 ? (
        <p className="mt-4 text-sm text-[var(--muted)]">
          Add numeric chat IDs to{" "}
          <code className="text-[var(--ink)]">TELEGRAM_ALLOWED_CHAT_IDS</code> and restart. Blocked
          chats still appear in activity below.
        </p>
      ) : null}

      {status.error_type && status.runtime === "error" ? (
        <p className="mt-4 text-sm text-[var(--danger)]" role="alert">
          Last error: {status.error_type}. Check the token and the backend logs.
        </p>
      ) : null}

      <p className="mt-4 text-xs leading-5 text-[var(--muted)]">
        Only allowlisted chats receive replies. Run{" "}
        <code className="text-[var(--ink)]">{status.command}</code> instead of the dashboard only if
        you need a separate CLI bot.
      </p>
    </section>
  );
}
