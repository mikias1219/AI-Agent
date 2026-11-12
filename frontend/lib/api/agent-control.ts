import { api } from "./client";

export type AutonomyPresetId = "ask_first" | "balanced" | "proactive";

export type AgentControlState = {
  autonomy_preset: AutonomyPresetId;
  paused: boolean;
  budgets: {
    commits_used: number;
    commits_cap: number;
    proactive_used: number;
    proactive_cap: number;
  };
};

export const AUTONOMY_LABELS: Record<AutonomyPresetId, string> = {
  ask_first: "Ask first",
  balanced: "Balanced",
  proactive: "Proactive",
};

export function getAgentControl() {
  return api<AgentControlState>("/agent/control");
}

export function patchAgentControl(input: { autonomy_preset?: AutonomyPresetId; paused?: boolean }) {
  return api<AgentControlState>("/agent/control", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
