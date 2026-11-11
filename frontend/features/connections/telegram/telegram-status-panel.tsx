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
  const connected = isConnected(status);
  const acting = isActingAsYou(status);
  const title = status.username ? `@${status.username}` : "Telegram";
  const stateLabel = !connected
    ? "Not connected"
    : acting
      ? "Acting as you"
      : "Connected · waiting";
  const hint = !status.configured
    ? "Add TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_CHAT_IDS on the server, then restart."
    : status.allowed_chat_ids.length === 0
      ? "Add allowlisted chat IDs on the server so the agent can reply."
      : acting
        ? "Listening for questions and requests in your allowlisted chats."
        : `Status: ${runtimeLabel(status.runtime)}. Last seen ${
            status.last_seen ? formatWhen(status.last_seen) : "not yet"
          }.`;

  return (
    <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-5 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Status</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--ink)]">{title}</h2>
          <p className="mt-1 text-sm font-medium text-[var(--ink)]" role="status">
            {stateLabel}
          </p>
          <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">{hint}</p>
        </div>
        <Radio
          className={`mt-1 h-5 w-5 shrink-0 ${
            connected ? "text-[var(--success)]" : "text-[var(--muted)]"
          }`}
          aria-hidden
        />
      </div>
      {connected ? (
        <p className="mt-4 text-xs text-[var(--muted)]">
          {status.allowed_chat_ids.length} allowlisted chat
          {status.allowed_chat_ids.length === 1 ? "" : "s"}
        </p>
      ) : null}
      {status.error_type && status.runtime === "error" ? (
        <p className="mt-3 text-sm text-[var(--danger)]" role="alert">
          Something went wrong ({status.error_type}). Check the bot token and try again later.
        </p>
      ) : null}
    </section>
  );
}
