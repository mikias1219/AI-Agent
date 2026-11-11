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
import { apiErrorMessage } from "@/lib/api/client";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { listApprovals } from "@/lib/api/approvals";
import { createTask, listTasks, patchTask } from "@/lib/api/tasks";
import type { Approval, Task, TaskPriority, TaskStatus } from "@/lib/api/types";
import { paginate } from "@/lib/pagination";
import { NEXT_STATUS, STATUS_LABEL, TaskDetailDrawer } from "./task-detail-drawer";
import {
  PRIORITY_OPTIONS,
  TASK_VIEWS,
  VIEW_EMPTY,
  dueInfo,
  priorityLabel,
  priorityTone,
  viewParams,
  type TaskViewId,
} from "./task-views";

export const TASK_PAGE_SIZE = 10;

type Section = "tasks" | "approvals";

const STATUS_TONE: Record<TaskStatus, BadgeTone> = {
  planned: "neutral",
  in_progress: "accent",
  blocked: "warning",
  done: "success",
  cancelled: "neutral",
};

const selectClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)]";

export function TasksPage() {
  const [section, setSection] = useState<Section>("tasks");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [taskPage, setTaskPage] = useState(1);
  const [approvalPage, setApprovalPage] = useState(1);
  const [title, setTitle] = useState("");
  const [view, setView] = useState<TaskViewId>("all");
  const [dueInput, setDueInput] = useState("");
  const [priorityInput, setPriorityInput] = useState<TaskPriority>("none");
  const [detail, setDetail] = useState<Task | null>(null);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const load = useCallback(
    async (options?: { initial?: boolean }) => {
      if (options?.initial) setLoading(true);
      setError(null);
      try {
        const [nextTasks, nextApprovals] = await Promise.all([
          listTasks(viewParams(view)),
          listApprovals(),
        ]);
        setTasks(nextTasks);
        setApprovals(nextApprovals);
      } catch (err) {
        setError(apiErrorMessage(err));
      } finally {
        if (options?.initial) setLoading(false);
      }
    },
    [view],
  );

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
      await createTask({
        title: nextTitle,
        ...(priorityInput !== "none" ? { priority: priorityInput } : {}),
        ...(dueInput ? { due_at: dueInput } : {}),
      });
      setTitle("");
      setDueInput("");
      setPriorityInput("none");
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
      await patchTask(task.id, { status });
      await load();
    } catch (err) {
      setStatusError(apiErrorMessage(err));
    } finally {
      setUpdatingId(null);
    }
  }

  function onSaved(updated: Task) {
    setDetail(updated);
    void load();
  }

  function onReplaced(replacement: Approval) {
    setApprovals((prev) =>
      prev.map((item) => (item.id === replacement.edited_from ? replacement : item)),
    );
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
          <Tabs
            items={TASK_VIEWS}
            value={view}
            onChange={(id) => {
              setView(id as TaskViewId);
              setTaskPage(1);
              setStatusError(null);
            }}
          />

          <form
            onSubmit={onCreate}
            className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
          >
            <Field label="New task" htmlFor="new-task-title" error={titleError ?? undefined}>
              <Input
                id="new-task-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={256}
                placeholder="What needs to get done?"
                disabled={creating}
              />
            </Field>
            <div className="flex flex-wrap items-end gap-3">
              <Field label="Due (optional)" htmlFor="new-task-due" className="min-w-[12rem]">
                <Input
                  id="new-task-due"
                  type="datetime-local"
                  value={dueInput}
                  onChange={(event) => setDueInput(event.target.value)}
                  disabled={creating}
                />
              </Field>
              <Field label="Priority" htmlFor="new-task-priority" className="min-w-[10rem]">
                <select
                  id="new-task-priority"
                  className={selectClass}
                  value={priorityInput}
                  onChange={(event) => setPriorityInput(event.target.value as TaskPriority)}
                  disabled={creating}
                >
                  {PRIORITY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="ml-auto">
                <Button
                  type="submit"
                  size="sm"
                  loading={creating}
                  disabled={creating || !title.trim()}
                >
                  Add task
                </Button>
              </div>
            </div>
            {formError ? (
              <p className="text-sm text-[var(--danger)]" role="alert">
                {formError}
              </p>
            ) : null}
          </form>

          {statusError ? (
            <p className="text-sm text-[var(--danger)]" role="alert">
              {statusError}
            </p>
          ) : null}

          {tasks.length === 0 ? (
            <EmptyState title={VIEW_EMPTY[view].title} description={VIEW_EMPTY[view].description} />
          ) : (
            <ul className="flex flex-col gap-2">
              {pagedTasks.items.map((task) => {
                const next = NEXT_STATUS[task.status] ?? [];
                const due = dueInfo(task);
                const priority = priorityLabel(task.priority);
                return (
                  <li
                    key={task.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      aria-label={`Open ${task.title}`}
                      onClick={() => setDetail(task)}
                    >
                      <p className="text-sm font-medium break-words text-[var(--ink)]">
                        {task.title}
                      </p>
                      {task.description ? (
                        <p className="mt-1 line-clamp-2 text-sm break-words text-[var(--muted)]">
                          {task.description}
                        </p>
                      ) : null}
                    </button>
                    <div className="flex flex-wrap items-center gap-2">
                      {priority ? (
                        <Badge tone={priorityTone(task.priority)}>{priority}</Badge>
                      ) : null}
                      {due ? <Badge tone={due.tone}>{due.label}</Badge> : null}
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
            <ul className="flex flex-col gap-3">
              {pagedApprovals.items.map((approval) => (
                <li key={approval.id}>
                  <ApprovalCard
                    approval={approval}
                    onDecided={() => void load()}
                    onReplaced={onReplaced}
                  />
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

      <TaskDetailDrawer task={detail} onClose={() => setDetail(null)} onSaved={onSaved} />
    </div>
  );
}
