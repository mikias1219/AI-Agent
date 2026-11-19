"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { ActivityPage } from "@/features/activity/activity-page";
import { AutomationsPage } from "@/features/automations/automations-page";

export type AgentHubProps = {
  section: "routines" | "activity";
};

export function AgentHub({ section }: AgentHubProps) {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <HubChrome
        eyebrow="Agent"
        title="Routines and activity"
        description="Scheduled work AURA runs for you, and a clear log of what already happened."
        tabs={[
          { id: "routines", label: "Routines", href: "/routines" },
          { id: "activity", label: "Activity", href: "/activity" },
        ]}
      />
      {section === "routines" ? <AutomationsPage embedded /> : <ActivityPage embedded />}
    </div>
  );
}
