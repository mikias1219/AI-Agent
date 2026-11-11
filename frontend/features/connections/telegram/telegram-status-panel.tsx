"use client";

import { Radio } from "lucide-react";
import type { TelegramStatusPayload } from "@/lib/api/types";
import {
  resolveTelegramAgentState,
  telegramAgentStatusHint,
  telegramAgentStatusLabel,
} from "./agent-state";

export type TelegramStatusPanelProps = {
  status: TelegramStatusPayload;
};

export function TelegramStatusPanel({ status }: TelegramStatusPanelProps) {
  const state = resolveTelegramAgentState(status);
  const title = status.username ? `@${status.username}` : "Telegram";
  const listening = state === "listening";

  return (
    <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-5 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Status</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--ink)]">{title}</h2>
          <p className="mt-1 text-sm font-medium text-[var(--ink)]" role="status">
            {telegramAgentStatusLabel(state)}
          </p>
          <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
            {telegramAgentStatusHint(state, status)}
          </p>
        </div>
        <Radio
          className={`mt-1 h-5 w-5 shrink-0 ${
            listening ? "text-[var(--success)]" : "text-[var(--muted)]"
          }`}
          aria-hidden
        />
      </div>
      {status.configured && status.allowed_chat_ids.length > 0 ? (
        <p className="mt-4 text-xs text-[var(--muted)]">
          {status.allowed_chat_ids.length} allowlisted chat
          {status.allowed_chat_ids.length === 1 ? "" : "s"}
        </p>
      ) : null}
    </section>
  );
}
