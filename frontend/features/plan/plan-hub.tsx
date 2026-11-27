"use client";

import { useCallback, useEffect, useState } from "react";
import { HubChrome } from "@/components/shell/hub-chrome";
import { planInsight } from "@/features/module-agent/insights";
import { ModuleAgent } from "@/features/module-agent/module-agent";
import { getNavCounts } from "@/lib/api/today";
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
  const [insight, setInsight] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  const loadInsight = useCallback(() => {
    getNavCounts()
      .then((counts) => setInsight(planInsight(counts.tasks_left, counts.tasks_untimed)))
      .catch(() => setInsight(null));
  }, []);

  useEffect(() => {
    loadInsight();
  }, [loadInsight, section]);

  return (
    <PageFrame>
      <HubChrome label="Plan" tabs={TABS} />
      <ModuleAgent
        module="plan"
        insight={insight}
        onDataChanged={() => {
          loadInsight();
          // Remount the open tab so it reloads anything the agent created or moved.
          setVersion((v) => v + 1);
          window.dispatchEvent(new Event("compass:data-changed"));
        }}
      />
      <div key={version} className="contents">
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
      </div>
    </PageFrame>
  );
}
