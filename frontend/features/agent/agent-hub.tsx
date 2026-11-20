"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { PageFrame } from "@/components/ui/page-frame";
import { ActivityPage } from "@/features/activity/activity-page";
import { AgentOverview } from "@/features/agent/agent-overview";
import { AutomationsPage } from "@/features/automations/automations-page";
import { ConnectionsPage } from "@/features/connections/connections-page";
import { MemoryPage } from "@/features/memory/memory-page";

export type AgentHubProps = {
  section: "overview" | "memory" | "routines" | "activity" | "connections";
};

const TABS = [
  { id: "overview", label: "Overview", href: "/agent" },
  { id: "memory", label: "Memory", href: "/memory" },
  { id: "routines", label: "Routines", href: "/routines" },
  { id: "activity", label: "Activity", href: "/activity" },
  { id: "connections", label: "Connections", href: "/connections" },
];

export function AgentHub({ section }: AgentHubProps) {
  return (
    <PageFrame>
      <HubChrome label="Agent" tabs={TABS} />
      {section === "overview" ? <AgentOverview /> : null}
      {section === "memory" ? <MemoryPage embedded /> : null}
      {section === "routines" ? <AutomationsPage embedded /> : null}
      {section === "activity" ? <ActivityPage embedded /> : null}
      {section === "connections" ? <ConnectionsPage embedded /> : null}
    </PageFrame>
  );
}
