import { api } from "./client";
import type { ActivityEvent } from "./types";

export type TelegramIdentity = {
  id?: number | string | null;
  username?: string | null;
  name?: string | null;
};

export type TelegramCommandResult = {
  requested: "start" | "stop";
};

export async function verifyTelegram(): Promise<TelegramIdentity> {
  return api<TelegramIdentity>("/telegram/verify", { method: "POST" });
}

export async function startTelegram(): Promise<TelegramCommandResult> {
  return api<TelegramCommandResult>("/telegram/start", { method: "POST" });
}

export async function stopTelegram(): Promise<TelegramCommandResult> {
  return api<TelegramCommandResult>("/telegram/stop", { method: "POST" });
}

export async function telegramActivity(limit = 50): Promise<ActivityEvent[]> {
  const safe = Math.min(200, Math.max(1, Math.trunc(limit)));
  return api<ActivityEvent[]>(`/telegram/activity?limit=${safe}`);
}
