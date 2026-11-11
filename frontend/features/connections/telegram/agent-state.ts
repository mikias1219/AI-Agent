import type { TelegramStatusPayload } from "@/lib/api/types";
import type { BadgeTone } from "@/components/ui/badge";

export type TelegramAgentUiState = "listening" | "starting" | "needs_setup" | "error";

type StatusCore = Pick<
  TelegramStatusPayload,
  "configured" | "allowed_chat_ids" | "managed" | "runtime"
>;

export function resolveTelegramAgentState(status: StatusCore): TelegramAgentUiState {
  if (!status.configured || status.allowed_chat_ids.length === 0) return "needs_setup";
  if (status.runtime === "error") return "error";
  if (status.managed) return "listening";
  return "starting";
}

export function telegramAgentStatusLabel(state: TelegramAgentUiState): string {
  switch (state) {
    case "listening":
      return "Listening";
    case "starting":
      return "Starting";
    case "needs_setup":
      return "Needs setup";
    case "error":
      return "Error";
  }
}

export function telegramAgentStatusHint(
  state: TelegramAgentUiState,
  status: TelegramStatusPayload,
): string {
  switch (state) {
    case "listening":
      return "Agent is listening in your allowlisted chats.";
    case "starting":
      return "Starting your Telegram agent…";
    case "needs_setup":
      if (!status.configured) {
        return "Add TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_CHAT_IDS on the server, then restart.";
      }
      return "Add allowlisted chat IDs on the server so the agent can reply.";
    case "error":
      return status.error_type
        ? `Something went wrong (${status.error_type}). Check the bot token and try again later.`
        : "Something went wrong. Check the bot token and try again later.";
  }
}

export function telegramOverviewCopy(state: TelegramAgentUiState): {
  value: string;
  detail: string;
} {
  switch (state) {
    case "listening":
      return { value: "Listening", detail: "Agent replies in Telegram" };
    case "starting":
      return { value: "Starting", detail: "Starting your Telegram agent" };
    case "needs_setup":
      return { value: "Needs setup", detail: "Open Telegram page" };
    case "error":
      return { value: "Error", detail: "See Telegram page" };
  }
}

export function telegramHealthChip(state: TelegramAgentUiState): {
  statusLabel: string;
  tone: BadgeTone;
} {
  switch (state) {
    case "listening":
      return { statusLabel: "Listening", tone: "success" };
    case "starting":
      return { statusLabel: "Starting", tone: "accent" };
    case "needs_setup":
      return { statusLabel: "Needs setup", tone: "neutral" };
    case "error":
      return { statusLabel: "Error", tone: "warning" };
  }
}

export function telegramChannelCardCopy(state: TelegramAgentUiState): {
  badge: string;
  tone: BadgeTone;
  description: string;
} {
  switch (state) {
    case "listening":
      return {
        badge: "Listening",
        tone: "success",
        description: "Your always-on agent replies in allowlisted Telegram chats.",
      };
    case "starting":
      return {
        badge: "Starting",
        tone: "accent",
        description: "Starting your Telegram agent…",
      };
    case "needs_setup":
      return {
        badge: "Needs setup",
        tone: "neutral",
        description: "Open Telegram for setup steps.",
      };
    case "error":
      return {
        badge: "Error",
        tone: "warning",
        description: "Open Telegram to see what went wrong.",
      };
  }
}
