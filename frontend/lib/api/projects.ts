import { api } from "./client";

export type ProjectStatus = "active" | "paused" | "done" | "archived";

export type Project = {
  id: string;
  name: string;
  status: ProjectStatus;
  deadline: string | null;
  notes: string;
  tasks: { done: number; open: number; overdue: number; total: number };
  progress_pct: number;
  days_left: number | null;
};

export const listProjects = () => api<Project[]>("/projects");
export const createProject = (body: { name: string; deadline?: string; notes?: string }) =>
  api<Project>("/projects", { method: "POST", body: JSON.stringify(body) });
export const patchProject = (
  id: string,
  body: Partial<Pick<Project, "name" | "status" | "deadline" | "notes">>,
) => api<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) });
export const deleteProject = (id: string) =>
  api<unknown>(`/projects/${id}`, { method: "DELETE" }).catch(() => undefined);
