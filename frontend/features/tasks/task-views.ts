import type { ListTasksParams } from "@/lib/api/tasks";
import type { Task, TaskPriority } from "@/lib/api/types";
import type { BadgeTone } from "@/components/ui/badge";

export type TaskViewId = "today" | "upcoming" | "overdue" | "all" | "done";

export const TASK_VIEWS: { id: TaskViewId; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "upcoming", label: "Upcoming" },
  { id: "overdue", label: "Overdue" },
  { id: "all", label: "All" },
  { id: "done", label: "Done" },
];

export const VIEW_EMPTY: Record<TaskViewId, { title: string; description: string }> = {
  today: { title: "Nothing due today", description: "Tasks due today will show up here." },
  upcoming: { title: "Nothing upcoming", description: "Tasks with a later due date show here." },
  overdue: { title: "Nothing overdue", description: "You are all caught up." },
  all: { title: "No tasks yet", description: "Add one above to start tracking work." },
  done: { title: "No completed tasks", description: "Finished tasks will show up here." },
};

/** Map a UI view to the `/api/tasks` query params. */
export function viewParams(view: TaskViewId): ListTasksParams {
  if (view === "done") return { status: "done" };
  if (view === "all") return {};
  return { view };
}

export const PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: "none", label: "No priority" },
  { value: "p1", label: "P1 · Urgent" },
  { value: "p2", label: "P2 · High" },
  { value: "p3", label: "P3 · Normal" },
];

export function priorityLabel(priority: TaskPriority): string {
  return priority === "none" ? "" : priority.toUpperCase();
}

export function priorityTone(priority: TaskPriority): BadgeTone {
  if (priority === "p1") return "warning";
  if (priority === "p2") return "accent";
  return "neutral";
}

export type DueInfo = { label: string; tone: BadgeTone; overdue: boolean };

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/** Describe a due date relative to `now` (browser-local days). Returns null when unset/invalid. */
export function dueInfo(
  task: Pick<Task, "due_at" | "status">,
  now: Date = new Date(),
): DueInfo | null {
  if (!task.due_at) return null;
  const due = new Date(task.due_at);
  if (Number.isNaN(due.getTime())) return null;
  const open = task.status !== "done" && task.status !== "cancelled";
  const today = startOfDay(now).getTime();
  const dayDiff = Math.round((startOfDay(due).getTime() - today) / 86_400_000);
  const time = new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(due);
  const hasTime = due.getHours() !== 0 || due.getMinutes() !== 0;
  const day =
    dayDiff === 0
      ? "Today"
      : dayDiff === 1
        ? "Tomorrow"
        : dayDiff === -1
          ? "Yesterday"
          : new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(due);
  const label = hasTime ? `${day}, ${time}` : day;
  if (open && dayDiff < 0) return { label: `Overdue · ${label}`, tone: "warning", overdue: true };
  if (open && dayDiff === 0) return { label, tone: "accent", overdue: false };
  return { label, tone: "neutral", overdue: false };
}

/** Convert an ISO instant to a `datetime-local` input value (browser-local). */
export function toDateTimeLocal(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
