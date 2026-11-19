"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { GoalsPage } from "@/features/goals/goals-page";
import { TasksPage } from "@/features/tasks/tasks-page";

export type WorkHubProps = {
  section: "tasks" | "goals";
};

export function WorkHub({ section }: WorkHubProps) {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <HubChrome
        eyebrow="Work"
        title="Tasks and goals"
        description="What needs doing today, and longer outcomes AURA can plan with you."
        tabs={[
          { id: "tasks", label: "Tasks", href: "/tasks" },
          { id: "goals", label: "Goals", href: "/goals" },
        ]}
      />
      {section === "tasks" ? <TasksPage embedded /> : <GoalsPage embedded />}
    </div>
  );
}
