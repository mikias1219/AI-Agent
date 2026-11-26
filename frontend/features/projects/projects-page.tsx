"use client";

import { FormEvent, useState } from "react";
import { FolderKanban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { StatusChip } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { createProject, listProjects, patchProject, type Project } from "@/lib/api/projects";
import { formatDate } from "@/lib/format-date";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";

function deadlineChip(project: Project) {
  if (project.days_left === null || project.status === "done") return null;
  if (project.days_left < 0)
    return <StatusChip tone="danger">{-project.days_left} days late</StatusChip>;
  if (project.days_left <= 7)
    return <StatusChip tone="warning">{project.days_left} days left</StatusChip>;
  return <StatusChip>{formatDate(project.deadline as string)}</StatusChip>;
}

/** Projects group tasks by name. Progress is counted from the tasks themselves. */
export function ProjectsPage({ embedded = false }: { embedded?: boolean }) {
  void embedded;
  const { toast } = useToast();
  const projects = useLoad(listProjects);
  const [name, setName] = useState("");
  const [deadline, setDeadline] = useState("");
  const [busy, setBusy] = useState(false);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      await createProject({ name: name.trim(), ...(deadline ? { deadline } : {}) });
      setName("");
      setDeadline("");
      await projects.reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(project: Project, status: Project["status"]) {
    try {
      await patchProject(project.id, { status });
      await projects.reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  if (projects.error)
    return (
      <ErrorBlock what="projects" message={projects.error} onRetry={() => void projects.reload()} />
    );
  if (!projects.data) return <CardSkeleton rows={3} />;
  const visible = projects.data.filter((p) => p.status !== "archived");

  return (
    <div className="flex flex-col gap-5">
      <Card
        id="project-new"
        title="New project"
        description="Give tasks the same project name to group them here."
      >
        <form onSubmit={onCreate} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Field label="Name" htmlFor="project-name" className="flex-1">
            <Input
              id="project-name"
              className="min-h-11"
              maxLength={128}
              value={name}
              placeholder="e.g. Website redesign"
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <Field label="Deadline (optional)" htmlFor="project-deadline">
            <Input
              id="project-deadline"
              type="date"
              className="min-h-11"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
            />
          </Field>
          <Button type="submit" className="min-h-11" loading={busy} disabled={!name.trim()}>
            Add project
          </Button>
        </form>
      </Card>

      {visible.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects yet"
          description="Create one, then set the same project on your tasks to see progress here."
        />
      ) : (
        visible.map((p) => (
          <Card
            key={p.id}
            id={`project-${p.id}`}
            title={p.name}
            description={`${p.tasks.done} of ${p.tasks.total} tasks done${p.tasks.overdue ? ` · ${p.tasks.overdue} overdue` : ""}`}
            action={deadlineChip(p)}
          >
            <div className="flex flex-col gap-3">
              <div
                className="h-2 overflow-hidden rounded-full bg-[var(--subtle)]"
                role="progressbar"
                aria-label={`${p.name} progress`}
                aria-valuenow={p.progress_pct}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full rounded-full bg-[var(--accent)]"
                  style={{ width: `${p.progress_pct}%` }}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {p.status !== "done" ? (
                  <Button size="sm" variant="secondary" onClick={() => void setStatus(p, "done")}>
                    Mark done
                  </Button>
                ) : (
                  <Button size="sm" variant="secondary" onClick={() => void setStatus(p, "active")}>
                    Reopen
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => void setStatus(p, "archived")}>
                  Archive
                </Button>
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  );
}
