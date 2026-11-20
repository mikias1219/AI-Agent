"use client";

import { useEffect, useState } from "react";
import { Mail, Puzzle, Send } from "lucide-react";
import { getGoogleStatus } from "@/lib/api/google";
import { listMcpServers } from "@/lib/api/mcp";
import { getStatus } from "@/lib/api/status";
import type { TelegramStatusPayload } from "@/lib/api/types";
import { ChannelCard } from "./channel-card";
import { googleCard, mcpCard, telegramCard, type Loaded } from "./channel-status";

/** Pass a stable (module-level) loader so the request runs once. */
function useLoaded<T>(load: () => Promise<T>): Loaded<T> {
  const [value, setValue] = useState<Loaded<T>>(undefined);
  useEffect(() => {
    let cancelled = false;
    load()
      .then((next) => {
        if (!cancelled) setValue(next);
      })
      .catch(() => {
        if (!cancelled) setValue(null);
      });
    return () => {
      cancelled = true;
    };
  }, [load]);
  return value;
}

async function loadTelegramStatus(): Promise<TelegramStatusPayload> {
  return (await getStatus()).telegram;
}

export function ChannelGrid() {
  const telegram = useLoaded(loadTelegramStatus);
  const google = useLoaded(getGoogleStatus);
  const mcp = useLoaded(listMcpServers);

  const telegramCopy = telegramCard(telegram);
  const googleCopy = googleCard(google);
  const mcpCopy = mcpCard(mcp);

  return (
    <ul className="grid gap-4 sm:grid-cols-2">
      <ChannelCard
        href="/connections/google"
        name="Google"
        description={googleCopy.description}
        badge={googleCopy.badge}
        tone={googleCopy.tone}
        icon={<Mail className="h-4 w-4" aria-hidden />}
      />
      <ChannelCard
        href="/connections/telegram"
        name="Telegram"
        description={telegramCopy.description}
        badge={telegramCopy.badge}
        tone={telegramCopy.tone}
        icon={<Send className="h-4 w-4" aria-hidden />}
      />
      <ChannelCard
        href="/connections/mcp"
        name="Extra tools (MCP)"
        description={mcpCopy.description}
        badge={mcpCopy.badge}
        tone={mcpCopy.tone}
        icon={<Puzzle className="h-4 w-4" aria-hidden />}
      />
    </ul>
  );
}
