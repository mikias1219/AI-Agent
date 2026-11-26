"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { PageFrame } from "@/components/ui/page-frame";
import { CalendarPage } from "@/features/calendar/calendar-page";
import { HabitsPage } from "@/features/habits/habits-page";
import { GoalsPage } from "@/features/goals/goals-page";
import { ProjectsPage } from "@/features/projects/projects-page";
import { TimePage } from "@/features/time/time-page";
import { ReviewPage } from "@/features/review/review-page";
import { TasksPage } from "@/features/tasks/tasks-page";

export type PlanHubProps = {
  section: "tasks" | "habits" | "projects" | "goals" | "time" | "calendar" | "review";
};

const TABS = [
  { id: "tasks", label: "Tasks", href: "/tasks" },
  { id: "habits", label: "Habits", href: "/habits" },
  { id: "projects", label: "Projects", href: "/projects" },
  { id: "goals", label: "Goals", href: "/goals" },
  { id: "time", label: "Time", href: "/time" },
  { id: "calendar", label: "Calendar", href: "/calendar" },
  { id: "review", label: "Review", href: "/review" },
];

export function PlanHub({ section }: PlanHubProps) {
  return (
    <PageFrame>
      <HubChrome label="Plan" tabs={TABS} />
      {section === "tasks" ? <TasksPage embedded /> : null}
      {section === "habits" ? <HabitsPage embedded /> : null}
      {section === "projects" ? <ProjectsPage embedded /> : null}
      {section === "time" ? <TimePage embedded /> : null}
      {section === "goals" ? <GoalsPage embedded /> : null}
      {section === "review" ? <ReviewPage embedded /> : null}
      {section === "calendar" ? <CalendarPage embedded /> : null}
    </PageFrame>
  );
}
