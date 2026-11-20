import { api } from "./client";

export type AgentCapability = {
  name: string;
  access_kind: "read" | "prepare" | "execute" | "destructive" | string;
  description: string;
};

export type AgentCapabilities = {
  tools: AgentCapability[];
  counts: Record<string, number>;
};

export function getAgentCapabilities() {
  return api<AgentCapabilities>("/agent/capabilities");
}
