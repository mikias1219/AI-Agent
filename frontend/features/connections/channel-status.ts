import type { BadgeTone } from "@/components/ui/badge";
import type { GoogleStatus } from "@/lib/api/google";
import type { McpServer } from "@/lib/api/mcp";
import type { TelegramStatusPayload } from "@/lib/api/types";
import { resolveTelegramAgentState, telegramChannelCardCopy } from "./telegram/agent-state";

export type CardCopy = {
  badge: string;
  tone: BadgeTone;
  description: string;
};

/** One source per card: `undefined` while loading, `null` when the request failed. */
export type Loaded<T> = T | null | undefined;

const CHECKING: CardCopy = { badge: "Checking", tone: "neutral", description: "Reading status." };

function unavailable(what: string): CardCopy {
  return {
    badge: "Unavailable",
    tone: "warning",
    description: `Status could not be loaded. Open ${what} to try again.`,
  };
}

export function telegramCard(status: Loaded<TelegramStatusPayload>): CardCopy {
  if (status === undefined) return CHECKING;
  if (status === null) return unavailable("Telegram");
  const copy = telegramChannelCardCopy(resolveTelegramAgentState(status));
  return { badge: copy.badge, tone: copy.tone, description: copy.description };
}

export function googleCard(status: Loaded<GoogleStatus>): CardCopy {
  if (status === undefined) return CHECKING;
  if (status === null) return unavailable("Google");
  if (!status.oauth_configured) {
    return {
      badge: "Needs setup",
      tone: "neutral",
      description: "Google sign-in is not configured on the server yet.",
    };
  }
  if (!status.connected) {
    return {
      badge: "Not connected",
      tone: "neutral",
      description: "Connect Gmail, Calendar and Drive. Compass starts in read-only mode.",
    };
  }
  const account = status.email ? `Connected as ${status.email}. ` : "";
  return {
    badge: "Connected",
    tone: "success",
    description:
      status.read_only === false
        ? `${account}Can read, draft and change. Sending and changes ask you first.`
        : `${account}Read-only: Compass can read mail, calendar and files.`,
  };
}

export function mcpCard(servers: Loaded<McpServer[]>): CardCopy {
  if (servers === undefined) return CHECKING;
  if (servers === null) return unavailable("Extra tools");
  const active = servers.filter((server) => server.enabled && !server.blocked_reason);
  if (servers.length === 0) {
    return {
      badge: "None added",
      tone: "neutral",
      description:
        "Add an MCP server to give Compass more tools. Tools that change things ask first.",
    };
  }
  const blocked = servers.filter((server) => server.blocked_reason).length;
  return {
    badge: `${active.length} active`,
    tone: blocked > 0 ? "warning" : active.length > 0 ? "success" : "neutral",
    description:
      blocked > 0
        ? `${servers.length} added, ${blocked} blocked on this deployment.`
        : `${servers.length} added. Tools that change things ask you first.`,
  };
}
