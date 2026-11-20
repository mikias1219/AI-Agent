import { api } from "./client";

export type AutonomyPresetId = "ask_first" | "balanced" | "proactive";

export type ToolPermissionMode = "allow" | "ask" | "block";

export type AgentControlState = {
  autonomy_preset: AutonomyPresetId;
  paused: boolean;
  budgets: {
    commits_used: number;
    commits_cap: number;
    proactive_used: number;
    proactive_cap: number;
  };
  tool_permissions?: Record<string, ToolPermissionMode>;
};

export type AgentPermissionTool = {
  name: string;
  access_kind: string;
  description: string;
  mode: ToolPermissionMode;
  ceiling: boolean;
};

export const AUTONOMY_LABELS: Record<AutonomyPresetId, string> = {
  ask_first: "Ask first",
  balanced: "Balanced",
  proactive: "Proactive",
};

/**
 * What the backend does today, in the owner's words. Ask first: every execute/destructive
 * tool waits for approval. Balanced: creating a calendar event on your own calendar can
 * run with a 10-minute undo; send/reply/delete and other ceilings still ask. Proactive
 * remains preference-only. Change this copy in the same commit that changes the policy.
 */
export const AUTONOMY_TODAY =
  "Ask first waits before sending, calendar writes and deletes. Balanced lets calendar create run with a 10-minute Undo; email send and deletes still ask. Proactive is not active yet.";

export const AUTONOMY_IN_EFFECT: Record<AutonomyPresetId, boolean> = {
  ask_first: true,
  balanced: true,
  proactive: false,
};

export const AUTONOMY_BLURBS: Record<AutonomyPresetId, string> = {
  ask_first:
    "Sending, calendar changes and deleting wait for your approval. Reading, drafting and updating your own tasks do not.",
  balanced:
    "Familiar reversible actions on your own data (calendar create, and undo for tasks, reminders and drafts) run with a 10-minute Undo. Email send and deletes still ask.",
  proactive:
    "Planned: routine low-risk actions run and are reported afterwards. Not active yet, so this behaves like Ask first.",
};

export function getAgentControl() {
  return api<AgentControlState>("/agent/control");
}

export function patchAgentControl(input: {
  autonomy_preset?: AutonomyPresetId;
  paused?: boolean;
  tool_permissions?: Record<string, ToolPermissionMode>;
}) {
  return api<AgentControlState>("/agent/control", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function getAgentPermissions() {
  return api<{ tools: AgentPermissionTool[] }>("/agent/permissions");
}
