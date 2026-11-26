"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { SkeletonRows } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { apiErrorMessage } from "@/lib/api/client";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { listApprovals } from "@/lib/api/approvals";
import { SCHEDULE_CHOICES } from "@/lib/api/habits";
import { createTask, listTasks, patchTask, type LifeTask as Task } from "@/lib/api/tasks";
import type { Approval, TaskPriority, TaskStatus } from "@/lib/api/types";
import { paginate } from "@/lib/pagination";
import { DayView } from "./day-view";
import { outcomeText } from "./day-logic";
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

export type TasksPageProps = {
  /** When true, hub chrome owns the page title. */
  embedded?: boolean;
};

export function TasksPage({ embedded = false }: TasksPageProps) {
  const [section, setSection] = useState<Section>("tasks");
  const [layout, setLayout] = useState<"list" | "board">("list");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approvalPage, setApprovalPage] = useState(1);
  const [title, setTitle] = useState("");
  const [view, setView] = useState<TaskViewId>("day");
  const [dueInput, setDueInput] = useState("");
  const [priorityInput, setPriorityInput] = useState<TaskPriority>("none");
  const [repeatInput, setRepeatInput] = useState("none");
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
          view === "day" ? Promise.resolve([]) : listTasks(viewParams(view)),
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

  const taskColumns: Column<Task>[] = [
    {
      id: "title",
      header: "Task",
      sortValue: (task) => task.title.toLowerCase(),
      cell: (task) => (
        <button
          type="button"
          className="block min-w-0 max-w-full text-left"
          aria-label={`Open ${task.title}`}
          onClick={(event) => {
            event.stopPropagation();
            setDetail(task);
          }}
        >
          <span className="block truncate font-medium text-[var(--ink)]">{task.title}</span>
          {task.description ? (
            <span className="block truncate text-[length:var(--text-caption)] text-[var(--muted)]">
              {task.description}
            </span>
          ) : null}
          {task.blocked || task.subtasks?.total || task.recurrence ? (
            <span className="mt-0.5 flex flex-wrap gap-2 text-[length:var(--text-caption)] text-[var(--muted)]">
              {task.blocked ? (
                <span className="text-[var(--warning)]">Waiting on another task</span>
              ) : null}
              {task.subtasks?.total ? (
                <span>
                  {task.subtasks.done}/{task.subtasks.total} subtasks
                </span>
              ) : null}
              {task.recurrence ? <span>Repeats</span> : null}
            </span>
          ) : null}
        </button>
      ),
    },
    {
      id: "priority",
      header: "Priority",
      width: "w-24",
      hideOnMobile: true,
      sortValue: (task) => (task.priority === "none" ? "z" : task.priority),
      cell: (task) => {
        const label = priorityLabel(task.priority);
        return label ? (
          <Badge tone={priorityTone(task.priority)}>{label}</Badge>
        ) : (
          <span className="text-[var(--muted)]">—</span>
        );
      },
    },
    {
      id: "due",
      header: "Due",
      width: "w-36",
      sortValue: (task) => task.due_at ?? "9999",
      cell: (task) => {
        const due = dueInfo(task);
        return due ? (
          <Badge tone={due.tone}>{due.label}</Badge>
        ) : (
          <span className="text-[var(--muted)]">No date</span>
        );
      },
    },
    {
      id: "status",
      header: "Status",
      width: "w-36",
      sortValue: (task) => task.status,
      cell: (task) => (
        <Badge tone={STATUS_TONE[task.status] ?? "neutral"}>
          {outcomeText(task) ?? STATUS_LABEL[task.status] ?? task.status}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: "",
      width: "w-44",
      align: "right",
      cell: (task) => {
        const next = NEXT_STATUS[task.status] ?? [];
        if (next.length === 0) return null;
        return (
          <select
            aria-label={`Change status of ${task.title}`}
            className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1.5 text-sm text-[var(--ink)]"
            value=""
            disabled={updatingId === task.id}
            onClick={(event) => event.stopPropagation()}
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
        );
      },
    },
  ];

  const approvalPages = Math.max(1, Math.ceil(approvals.length / TASK_PAGE_SIZE));
  const safeApprovalPage = Math.min(approvalPage, approvalPages);
  const pagedApprovals = paginate(approvals, safeApprovalPage, TASK_PAGE_SIZE);

  const repeatRule = SCHEDULE_CHOICES.find((s) => s.id === repeatInput)?.rule;

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
        ...(repeatRule ? { recurrence: repeatRule } : {}),
      });
      setTitle("");
      setDueInput("");
      setPriorityInput("none");
      setRepeatInput("none");
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

  const body = (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs
          aria-label="Tasks"
          items={[
            ...TASK_VIEWS,
            ...(approvals.length > 0
              ? [{ id: "approvals", label: `Approvals (${approvals.length})` }]
              : []),
          ]}
          value={section === "approvals" ? "approvals" : view}
          onChange={(id) => {
            setStatusError(null);
            if (id === "approvals") {
              setSection("approvals");
              return;
            }
            setSection("tasks");
            setView(id as TaskViewId);
          }}
        />
        {section === "tasks" && view !== "day" ? (
          <div
            role="group"
            aria-label="Layout"
            className="inline-flex rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-0.5"
          >
            {(["list", "board"] as const).map((id) => (
              <button
                key={id}
                type="button"
                aria-pressed={layout === id}
                onClick={() => setLayout(id)}
                className={`min-h-9 rounded-md px-3 text-sm font-medium transition ${
                  layout === id
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "text-[var(--muted)] hover:text-[var(--ink)]"
                }`}
              >
                {id === "list" ? "List" : "Board"}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {loading ? <SkeletonRows count={4} /> : null}

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

      {!loading && !error && section === "tasks" && view === "day" ? <DayView /> : null}

      {!loading && !error && section === "tasks" && view !== "day" ? (
        <>
          <form
            onSubmit={onCreate}
            className="flex flex-col gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3"
          >
            <div className="flex items-end gap-2">
              <Field
                label="New task"
                htmlFor="new-task-title"
                error={titleError ?? undefined}
                className="min-w-0 flex-1"
              >
                <Input
                  id="new-task-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  maxLength={256}
                  placeholder="What needs to get done?"
                  disabled={creating}
                />
              </Field>
              <Button type="submit" loading={creating} disabled={creating || !title.trim()}>
                Add task
              </Button>
            </div>
            <details className="text-sm">
              <summary className="min-h-9 cursor-pointer py-1.5 text-[var(--muted)] hover:text-[var(--ink)]">
                Options: due date, priority and repeat
              </summary>
              <div className="mt-2 flex flex-wrap items-end gap-3">
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
                <Field label="Repeats" htmlFor="new-task-repeat" className="min-w-[10rem]">
                  <select
                    id="new-task-repeat"
                    className={selectClass}
                    value={repeatInput}
                    onChange={(event) => setRepeatInput(event.target.value)}
                    disabled={creating}
                  >
                    <option value="none">Does not repeat</option>
                    {SCHEDULE_CHOICES.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
            </details>
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
          ) : layout === "board" ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {(["planned", "in_progress", "blocked", "done"] as TaskStatus[]).map((column) => {
                const columnTasks = tasks.filter((task) => task.status === column);
                return (
                  <section
                    key={column}
                    className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3"
                  >
                    <h3 className="mb-2 text-xs font-medium tracking-wide text-[var(--muted)] uppercase">
                      {STATUS_LABEL[column]} · {columnTasks.length}
                    </h3>
                    <ul className="flex flex-col gap-2">
                      {columnTasks.map((task) => (
                        <li key={task.id}>
                          <button
                            type="button"
                            onClick={() => setDetail(task)}
                            className="w-full rounded-md border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-left hover:border-[var(--accent)]"
                          >
                            <p className="text-sm font-medium text-[var(--ink)]">{task.title}</p>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </section>
                );
              })}
            </div>
          ) : (
            <Card id="tasks-table" title="Tasks" description={`${tasks.length} in this view`} flush>
              <DataTable
                label="Tasks"
                columns={taskColumns}
                rows={tasks}
                rowKey={(task) => task.id}
                pageSize={TASK_PAGE_SIZE}
                onRowClick={(task) => setDetail(task)}
                selectedKey={detail?.id ?? null}
              />
            </Card>
          )}
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
    </>
  );

  if (embedded) {
    return <div className="flex flex-col gap-5">{body}</div>;
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
      {body}
    </div>
  );
}
