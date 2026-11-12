"use client";

import { useEffect, useState } from "react";
import { Mail, Puzzle, Send } from "lucide-react";
import { getStatus } from "@/lib/api/status";
import type { TelegramStatusPayload } from "@/lib/api/types";
import { capabilities } from "@/lib/capabilities";
import {
  resolveTelegramAgentState,
  telegramChannelCardCopy,
} from "@/features/connections/telegram/agent-state";
import { ChannelCard } from "./channel-card";

type TelegramCard = {
  badge: string;
  tone: "neutral" | "accent" | "warning" | "success";
  description: string;
};

function telegramCard(
  status: TelegramStatusPayload | null,
  unavailable: boolean,
  loading: boolean,
): TelegramCard {
  if (loading) {
    return {
      badge: "Checking",
      tone: "neutral",
      description: "Reading Telegram agent status.",
    };
  }
  if (unavailable || !status) {
    return {
      badge: "Unavailable",
      tone: "warning",
      description: "Status could not be loaded. Open Telegram to try again.",
    };
  }
  const copy = telegramChannelCardCopy(resolveTelegramAgentState(status));
  return { badge: copy.badge, tone: copy.tone, description: copy.description };
}

function previewBadge(mode: "api" | "mock") {
  return mode === "mock"
    ? { badge: "Preview", tone: "neutral" as const }
    : { badge: "API", tone: "accent" as const };
}

export function ChannelGrid() {
  const [telegram, setTelegram] = useState<TelegramStatusPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getStatus()
      .then((status) => {
        if (!cancelled) setTelegram(status.telegram);
      })
      .catch(() => {
        if (!cancelled) setUnavailable(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const live = telegramCard(telegram, unavailable, loading);
  const google = previewBadge(capabilities.google);

  return (
    <div className="flex flex-col gap-4">
      {unavailable ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          Telegram status is unavailable. Preview channels below are sample data.
        </p>
      ) : null}
      <ul className="grid gap-4 sm:grid-cols-2">
        <ChannelCard
          href="/connections/telegram"
          name="Telegram"
          description={live.description}
          badge={live.badge}
          tone={live.tone}
          icon={<Send className="h-4 w-4" aria-hidden />}
        />
        <ChannelCard
          href="/connections/google"
          name="Google"
          description="Sample Gmail, Calendar, and Drive. Sign-in is not connected."
          badge={google.badge}
          tone={google.tone}
          icon={<Mail className="h-4 w-4" aria-hidden />}
        />
        <ChannelCard
          href="/connections/mcp"
          name="MCP"
          description="Connect stdio or HTTP MCP servers. Tools share the same approval gate."
          badge="API"
          tone="accent"
          icon={<Puzzle className="h-4 w-4" aria-hidden />}
        />
      </ul>
    </div>
  );
}
