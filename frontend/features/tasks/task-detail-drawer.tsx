"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/lib/api/client";
import { patchTask } from "@/lib/api/tasks";
import type { Task, TaskPriority, TaskStatus } from "@/lib/api/types";
import { PRIORITY_OPTIONS, toDateTimeLocal } from "./task-views";

export const STATUS_LABEL: Record<TaskStatus, string> = {
  planned: "Planned",
  in_progress: "In progress",
  blocked: "Blocked",
  done: "Done",
  cancelled: "Cancelled",
};

export const NEXT_STATUS: Record<TaskStatus, TaskStatus[]> = {
  planned: ["in_progress", "done", "cancelled"],
  in_progress: ["planned", "blocked", "done", "cancelled"],
  blocked: ["planned", "in_progress", "cancelled"],
  done: ["planned"],
  cancelled: ["planned"],
};

const selectClass =
  "w-full rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)]";

export type TaskDetailDrawerProps = {
  task: Task | null;
  onClose: () => void;
  onSaved: (task: Task) => void;
};

export function TaskDetailDrawer({ task, onClose, onSaved }: TaskDetailDrawerProps) {
  return (
    <Drawer open={task !== null} onClose={onClose} title="Task details">
      {task ? <TaskDetailForm key={task.id} task={task} onSaved={onSaved} /> : null}
    </Drawer>
  );
}

function TaskDetailForm({ task, onSaved }: { task: Task; onSaved: (task: Task) => void }) {
  const [title, setTitle] = useState(task.title);
  const [notes, setNotes] = useState(task.description);
  const [priority, setPriority] = useState<TaskPriority>(task.priority);
  const [due, setDue] = useState(toDateTimeLocal(task.due_at));
  const [status, setStatus] = useState<TaskStatus>(task.status);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const nextTitle = title.trim();
    if (!nextTitle) {
      setTitleError("Title is required.");
      return;
    }
    setTitleError(null);
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      const updated = await patchTask(task.id, {
        title: nextTitle,
        description: notes.trim(),
        priority,
        due_at: due || null,
        ...(status !== task.status ? { status } : {}),
      });
      onSaved(updated);
      setSaved(true);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const statusOptions = [task.status, ...NEXT_STATUS[task.status]];

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <Field label="Title" htmlFor="task-detail-title" error={titleError ?? undefined}>
        <Input
          id="task-detail-title"
          value={title}
          maxLength={256}
          onChange={(event) => setTitle(event.target.value)}
          disabled={saving}
        />
      </Field>
      <Field label="Notes" htmlFor="task-detail-notes">
        <Textarea
          id="task-detail-notes"
          value={notes}
          maxLength={10000}
          rows={4}
          onChange={(event) => setNotes(event.target.value)}
          disabled={saving}
        />
      </Field>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Priority" htmlFor="task-detail-priority">
          <select
            id="task-detail-priority"
            className={selectClass}
            value={priority}
            onChange={(event) => setPriority(event.target.value as TaskPriority)}
            disabled={saving}
          >
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Status" htmlFor="task-detail-status">
          <select
            id="task-detail-status"
            className={selectClass}
            value={status}
            onChange={(event) => setStatus(event.target.value as TaskStatus)}
            disabled={saving}
          >
            {statusOptions.map((value) => (
              <option key={value} value={value}>
                {STATUS_LABEL[value]}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="Due" htmlFor="task-detail-due">
        <div className="flex gap-2">
          <Input
            id="task-detail-due"
            type="datetime-local"
            value={due}
            onChange={(event) => setDue(event.target.value)}
            disabled={saving}
          />
          {due ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={saving}
              onClick={() => setDue("")}
            >
              Clear
            </Button>
          ) : null}
        </div>
      </Field>
      {task.project || task.tags.length > 0 ? (
        <p className="text-xs text-[var(--muted)]">
          {[task.project, ...task.tags.map((tag) => `#${tag}`)].filter(Boolean).join(" · ")}
        </p>
      ) : null}
      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}
      {saved ? (
        <p className="text-sm text-[var(--success)]" role="status">
          Saved.
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button type="submit" size="sm" loading={saving} disabled={saving || !title.trim()}>
          Save changes
        </Button>
      </div>
    </form>
  );
}
