"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { PageFrame } from "@/components/ui/page-frame";
import { CalendarPage } from "@/features/calendar/calendar-page";
import { GoalsPage } from "@/features/goals/goals-page";
import { TasksPage } from "@/features/tasks/tasks-page";

export type PlanHubProps = {
  section: "tasks" | "goals" | "calendar";
};

const TABS = [
  { id: "tasks", label: "Tasks", href: "/tasks" },
  { id: "goals", label: "Goals", href: "/goals" },
  { id: "calendar", label: "Calendar", href: "/calendar" },
];

export function PlanHub({ section }: PlanHubProps) {
  return (
    <PageFrame>
      <HubChrome label="Plan" tabs={TABS} />
      {section === "tasks" ? <TasksPage embedded /> : null}
      {section === "goals" ? <GoalsPage embedded /> : null}
      {section === "calendar" ? <CalendarPage embedded /> : null}
    </PageFrame>
  );
}
