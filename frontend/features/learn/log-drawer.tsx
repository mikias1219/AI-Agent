"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  createReadingLog,
  deleteReadingLog,
  updateReadingLog,
  type ReadingLog,
} from "@/lib/api/reading";
import { ConfirmModal } from "./confirm-modal";
import { explainPassageHref, localDateIso } from "./learn-logic";
import Link from "next/link";

export type LogDrawerState = { mode: "add" } | { mode: "edit"; log: ReadingLog } | null;

function LogForm({
  state,
  onClose,
  onSaved,
}: {
  state: NonNullable<LogDrawerState>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const log = state.mode === "edit" ? state.log : null;
  const [reference, setReference] = useState(log?.reference ?? "");
  const [readOn, setReadOn] = useState(log?.read_on ?? localDateIso());
  const [reflection, setReflection] = useState(log?.reflection ?? "");
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!reference.trim()) {
      setError("Add the passage you read, for example John 3:1-21.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (log) {
        await updateReadingLog(log.id, {
          reference: reference.trim(),
          read_on: readOn,
          reflection: reflection.trim(),
        });
      } else {
        await createReadingLog({
          reference: reference.trim(),
          read_on: readOn,
          reflection: reflection.trim(),
        });
      }
      toast("Saved.", "success");
      onSaved();
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!log) return;
    setBusy(true);
    try {
      await deleteReadingLog(log.id);
      toast("Deleted.", "success");
      onSaved();
      onClose();
    } catch (err) {
      setConfirmDelete(false);
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <Field label="Passage" htmlFor="lg-ref">
        <Input
          id="lg-ref"
          value={reference}
          maxLength={120}
          placeholder="e.g. John 3:1-21"
          className="min-h-11"
          onChange={(e) => setReference(e.target.value)}
        />
      </Field>
      <Field label="Date" htmlFor="lg-date">
        <Input
          id="lg-date"
          type="date"
          value={readOn}
          className="min-h-11"
          onChange={(e) => setReadOn(e.target.value)}
        />
      </Field>
      <Field label="Reflection (optional)" htmlFor="lg-reflection">
        <Textarea
          id="lg-reflection"
          value={reflection}
          maxLength={5000}
          rows={6}
          onChange={(e) => setReflection(e.target.value)}
        />
      </Field>
      {log ? (
        <Link
          href={explainPassageHref(log.reference)}
          className="text-sm text-[var(--accent)] underline-offset-2 hover:underline"
        >
          Ask Compass to explain this passage
        </Link>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {log ? (
          <Button
            variant="ghost"
            className="min-h-11 text-[var(--danger)]"
            onClick={() => setConfirmDelete(true)}
          >
            Delete
          </Button>
        ) : (
          <span />
        )}
        <div className="flex gap-2">
          <Button variant="secondary" className="min-h-11" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" className="min-h-11" loading={busy}>
            {log ? "Save" : "Log reading"}
          </Button>
        </div>
      </div>
      <ConfirmModal
        open={confirmDelete}
        title="Delete this entry?"
        message="The reading and its reflection will be removed from your log."
        confirmLabel="Delete"
        busy={busy}
        onConfirm={() => void remove()}
        onClose={() => setConfirmDelete(false)}
      />
    </form>
  );
}

export function LogDrawer({
  state,
  onClose,
  onSaved,
}: {
  state: LogDrawerState;
  onClose: () => void;
  onSaved: () => void;
}) {
  const key = state ? (state.mode === "edit" ? state.log.id : "add") : "closed";
  return (
    <Drawer
      open={state !== null}
      onClose={onClose}
      title={state?.mode === "edit" ? "Edit reading" : "Log a reading"}
    >
      {state ? <LogForm key={key} state={state} onClose={onClose} onSaved={onSaved} /> : null}
    </Drawer>
  );
}
