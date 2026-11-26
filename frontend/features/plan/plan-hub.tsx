"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { PageFrame } from "@/components/ui/page-frame";
import { CalendarPage } from "@/features/calendar/calendar-page";
import { GoalsPage } from "@/features/goals/goals-page";
import { HabitsPage } from "@/features/habits/habits-page";
import { ProjectsPage } from "@/features/projects/projects-page";
import { InsightsPage } from "@/features/review/insights-page";
import { TasksPage } from "@/features/tasks/tasks-page";

export type PlanHubProps = {
  section: "tasks" | "habits" | "goals" | "calendar" | "insights";
};

/** Five tabs. Projects live under Goals; the timer and the review live under Insights. */
const TABS = [
  { id: "tasks", label: "Tasks", href: "/tasks" },
  { id: "habits", label: "Habits", href: "/habits" },
  { id: "goals", label: "Goals", href: "/goals" },
  { id: "calendar", label: "Calendar", href: "/calendar" },
  { id: "insights", label: "Insights", href: "/review" },
];

export function PlanHub({ section }: PlanHubProps) {
  return (
    <PageFrame>
      <HubChrome label="Plan" tabs={TABS} />
      {section === "tasks" ? <TasksPage embedded /> : null}
      {section === "habits" ? <HabitsPage embedded /> : null}
      {section === "goals" ? (
        <div className="flex flex-col gap-8">
          <GoalsPage embedded />
          <section aria-labelledby="projects-heading" className="flex flex-col gap-3">
            <h2 id="projects-heading" className="text-base font-semibold text-[var(--ink)]">
              Projects
            </h2>
            <ProjectsPage embedded />
          </section>
        </div>
      ) : null}
      {section === "calendar" ? <CalendarPage embedded /> : null}
      {section === "insights" ? <InsightsPage /> : null}
    </PageFrame>
  );
}
