"use client";

import { FormEvent, useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/lib/api/client";
import { completeTask, type LifeTask, type TaskOutcome } from "@/lib/api/tasks";
import { OUTCOME_LABEL, suggestOutcome } from "./day-logic";

const CHOICES: TaskOutcome[] = ["achieved", "partial", "missed", "skipped"];

export type OutcomePanelProps = {
  task: LifeTask;
  onSaved: (task: LifeTask) => void;
  onCancel: () => void;
};

/** Inline "How did it go?" panel shown under a task when the owner checks it. */
export function OutcomePanel({ task, onSaved, onCancel }: OutcomePanelProps) {
  const uid = useId();
  const target = task.target_value && task.target_value > 0 ? task.target_value : null;
  const unit = task.target_unit?.trim() ?? "";
  const [actual, setActual] = useState(target !== null ? String(target) : "");
  const [outcome, setOutcome] = useState<TaskOutcome>("achieved");
  const [overridden, setOverridden] = useState(false);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onActual(value: string) {
    setActual(value);
    if (!overridden && value.trim() !== "" && Number.isFinite(Number(value))) {
      setOutcome(suggestOutcome(Number(value), target));
    }
  }

  const actualNumber = actual.trim() === "" ? null : Number(actual);
  const actualInvalid =
    actualNumber !== null && (!Number.isFinite(actualNumber) || actualNumber < 0);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (actualInvalid) {
      setError("Enter a number that is zero or more.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const updated = await completeTask(task.id, {
        outcome,
        ...(target !== null && actualNumber !== null && outcome !== "skipped"
          ? { actual_value: actualNumber }
          : {}),
        ...(note.trim() ? { note: note.trim() } : {}),
      });
      onSaved(updated);
    } catch (err) {
      setError(apiErrorMessage(err));
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      aria-label={`How did it go? ${task.title}`}
      className="mt-2 flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--accent-soft)] bg-[var(--canvas)] p-3"
    >
      <fieldset className="min-w-0">
        <legend className="mb-2 text-sm font-semibold text-[var(--ink)]">How did it go?</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {CHOICES.map((choice) => {
            const selected = outcome === choice;
            return (
              <label
                key={choice}
                className={`flex min-h-11 cursor-pointer items-center justify-center rounded-[var(--radius)] border px-3 text-sm font-medium transition has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-[var(--accent)] ${
                  selected
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--canvas)]"
                }`}
              >
                <input
                  type="radio"
                  name={`${uid}-outcome`}
                  value={choice}
                  checked={selected}
                  onChange={() => {
                    setOutcome(choice);
                    setOverridden(true);
                  }}
                  className="sr-only"
                />
                {OUTCOME_LABEL[choice]}
              </label>
            );
          })}
        </div>
      </fieldset>

      {target !== null ? (
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${uid}-actual`} className="text-sm font-medium text-[var(--ink)]">
            {`How many? (target ${target}${unit ? ` ${unit}` : ""})`}
          </label>
          <Input
            id={`${uid}-actual`}
            type="number"
            inputMode="decimal"
            min={0}
            step="any"
            value={actual}
            onChange={(event) => onActual(event.target.value)}
            disabled={saving || outcome === "skipped"}
            className="max-w-[10rem]"
          />
          <p className="text-[length:var(--text-caption)] text-[var(--muted)]">
            We suggest an outcome from the number. You can still pick a different one.
          </p>
        </div>
      ) : null}

      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${uid}-note`} className="text-sm font-medium text-[var(--ink)]">
          Note (optional)
        </label>
        <Input
          id={`${uid}-note`}
          value={note}
          maxLength={500}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Anything worth remembering?"
          disabled={saving}
        />
      </div>

      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button type="submit" loading={saving} className="min-h-11">
          Save
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={saving}
          className="min-h-11"
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
