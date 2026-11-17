import { api } from "@/lib/api/client";

export type AgentSkill = {
  name: string;
  description: string;
  version: string;
  workflow: string;
  tags: string[];
  tool_groups: string[];
};

export function listAgentSkills(): Promise<AgentSkill[]> {
  return api<AgentSkill[]>("/agent/skills");
}
