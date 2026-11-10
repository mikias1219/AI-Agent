"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { Tabs } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/lib/api/client";
import { createTask, decideApproval, listApprovals, listTasks, patchTask } from "@/lib/api/tasks";
import type { Approval, ApprovalDecision, Task, TaskStatus } from "@/lib/api/types";
import { paginate } from "@/lib/pagination";
import { TaskApproveModal } from "./task-approve-modal";

export const TASK_PAGE_SIZE = 10;

type Section = "tasks" | "approvals";

const STATUS_LABEL: Record<TaskStatus, string> = {
  planned: "Planned",
  in_progress: "In progress",
  blocked: "Blocked",
  done: "Done",
  cancelled: "Cancelled",
};

const STATUS_TONE: Record<TaskStatus, BadgeTone> = {
  planned: "neutral",
  in_progress: "accent",
  blocked: "warning",
  done: "success",
  cancelled: "neutral",
};

const NEXT_STATUS: Record<TaskStatus, TaskStatus[]> = {
  planned: ["in_progress", "cancelled"],
  in_progress: ["blocked", "done", "cancelled"],
  blocked: ["in_progress", "cancelled"],
  done: [],
  cancelled: [],
};

export function TasksPage() {
  const [section, setSection] = useState<Section>("tasks");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [taskPage, setTaskPage] = useState(1);
  const [approvalPage, setApprovalPage] = useState(1);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Approval | null>(null);
  const [pendingDecision, setPendingDecision] = useState<ApprovalDecision | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const load = useCallback(async (options?: { initial?: boolean }) => {
    if (options?.initial) setLoading(true);
    setError(null);
    try {
      const [nextTasks, nextApprovals] = await Promise.all([listTasks(), listApprovals()]);
      setTasks(nextTasks);
      setApprovals(nextApprovals);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      if (options?.initial) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load({ initial: true });
  }, [load]);

  const taskPages = Math.max(1, Math.ceil(tasks.length / TASK_PAGE_SIZE));
  const approvalPages = Math.max(1, Math.ceil(approvals.length / TASK_PAGE_SIZE));
  const safeTaskPage = Math.min(taskPage, taskPages);
  const safeApprovalPage = Math.min(approvalPage, approvalPages);
  const pagedTasks = paginate(tasks, safeTaskPage, TASK_PAGE_SIZE);
  const pagedApprovals = paginate(approvals, safeApprovalPage, TASK_PAGE_SIZE);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    const nextTitle = title.trim();
    if (!nextTitle) {
      setTitleError("Title is required.");
      return;
    }
    if (nextTitle.length > 256) {
      setTitleError("Title must be 256 characters or fewer.");
      return;
    }
    setTitleError(null);
    setFormError(null);
    setCreating(true);
    try {
      const descriptionText = description.trim();
      await createTask({
        title: nextTitle,
        ...(descriptionText ? { description: descriptionText } : {}),
      });
      setTitle("");
      setDescription("");
      setTaskPage(1);
      await load();
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function onStatus(task: Task, status: TaskStatus) {
    setStatusError(null);
    setUpdatingId(task.id);
    try {
      const updated = await patchTask(task.id, { status });
      setTasks((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setStatusError(apiErrorMessage(err));
    } finally {
      setUpdatingId(null);
    }
  }

  async function onDecide(decision: ApprovalDecision) {
    if (!selected) return;
    setDecisionError(null);
    setPendingDecision(decision);
    try {
      await decideApproval(selected.id, decision);
      setSelected(null);
      await load();
    } catch (err) {
      setDecisionError(apiErrorMessage(err));
    } finally {
      setPendingDecision(null);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Tasks</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Work and approvals
        </h1>
        <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
          Track tasks and decide agent actions that are waiting on you.
        </p>
      </header>

      <Tabs
        items={[
          { id: "tasks", label: "Tasks" },
          {
            id: "approvals",
            label: approvals.length > 0 ? `Approvals (${approvals.length})` : "Approvals",
          },
        ]}
        value={section}
        onChange={(id) => setSection(id as Section)}
      />

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-[var(--muted)]">
          <Spinner size="sm" />
          Loading…
        </div>
      ) : null}

      {!loading && error ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
          <Button variant="secondary" size="sm" onClick={() => void load({ initial: true })}>
            Try again
          </Button>
        </div>
      ) : null}

      {!loading && !error && section === "tasks" ? (
        <>
          <form
            onSubmit={onCreate}
            className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
          >
            <Field label="New task" error={titleError ?? undefined}>
              <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={256}
                placeholder="What needs to get done?"
                disabled={creating}
              />
            </Field>
            <Field label="Description">
              <Textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                maxLength={10000}
                rows={2}
                placeholder="Optional details"
                disabled={creating}
                className="min-h-[64px]"
              />
            </Field>
            {formError ? (
              <p className="text-sm text-[var(--danger)]" role="alert">
                {formError}
              </p>
            ) : null}
            <div className="flex justify-end">
              <Button type="submit" size="sm" loading={creating} disabled={creating || !title.trim()}>
                Add task
              </Button>
            </div>
          </form>

          {statusError ? (
            <p className="text-sm text-[var(--danger)]" role="alert">
              {statusError}
            </p>
          ) : null}

          {tasks.length === 0 ? (
            <EmptyState title="No tasks yet" description="Add one above to start tracking work." />
          ) : (
            <ul className="flex flex-col gap-2">
              {pagedTasks.items.map((task) => {
                const next = NEXT_STATUS[task.status] ?? [];
                return (
                  <li
                    key={task.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium break-words text-[var(--ink)]">{task.title}</p>
                      {task.description ? (
                        <p className="mt-1 line-clamp-3 text-sm break-words text-[var(--muted)]">
                          {task.description}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={STATUS_TONE[task.status] ?? "neutral"}>
                        {STATUS_LABEL[task.status] ?? task.status}
                      </Badge>
                      {next.length > 0 ? (
                        <select
                          aria-label={`Change status of ${task.title}`}
                          className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1.5 text-sm text-[var(--ink)]"
                          value=""
                          disabled={updatingId === task.id}
                          onChange={(event) => {
                            const status = event.target.value as TaskStatus;
                            if (status) void onStatus(task, status);
                          }}
                        >
                          <option value="" disabled>
                            Change status…
                          </option>
                          {next.map((status) => (
                            <option key={status} value={status}>
                              {STATUS_LABEL[status]}
                            </option>
                          ))}
                        </select>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {tasks.length > 0 ? (
            <Pagination
              page={pagedTasks.page}
              pageSize={pagedTasks.pageSize}
              total={pagedTasks.total}
              onPageChange={setTaskPage}
            />
          ) : null}
        </>
      ) : null}

      {!loading && !error && section === "approvals" ? (
        <>
          {approvals.length === 0 ? (
            <EmptyState
              title="Nothing waiting"
              description="Agent actions that need a decision will show up here."
            />
          ) : (
            <ul className="flex flex-col gap-2">
              {pagedApprovals.items.map((approval) => (
                <li
                  key={approval.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--ink)]">{approval.tool_name}</p>
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      {approval.actionable ? "Waiting for your decision" : "No longer waiting"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={approval.actionable ? "warning" : "neutral"}>
                      {approval.actionable ? "Actionable" : "Pending"}
                    </Badge>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setDecisionError(null);
                        setSelected(approval);
                      }}
                    >
                      Review
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {approvals.length > 0 ? (
            <Pagination
              page={pagedApprovals.page}
              pageSize={pagedApprovals.pageSize}
              total={pagedApprovals.total}
              onPageChange={setApprovalPage}
            />
          ) : null}
        </>
      ) : null}

      <TaskApproveModal
        approval={selected}
        open={selected !== null}
        pending={pendingDecision}
        error={decisionError}
        onClose={() => {
          if (pendingDecision) return;
          setSelected(null);
          setDecisionError(null);
        }}
        onDecide={(decision) => void onDecide(decision)}
      />
    </div>
  );
}
