"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  createLearnItem,
  deleteLearnItem,
  updateLearnItem,
  type LearnItem,
  type LearnKind,
} from "@/lib/api/learn";
import { ConfirmModal } from "./confirm-modal";
import { LANGUAGES } from "./learn-logic";

export type WordDrawerState = { mode: "add" } | { mode: "edit"; item: LearnItem } | null;

function WordForm({
  state,
  onClose,
  onSaved,
}: {
  state: NonNullable<WordDrawerState>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const item = state.mode === "edit" ? state.item : null;
  const [kind, setKind] = useState<LearnKind>(item?.kind ?? "word");
  const [term, setTerm] = useState(item?.term ?? "");
  const [meaning, setMeaning] = useState(item?.meaning ?? "");
  const [example, setExample] = useState(item?.example ?? "");
  const [language, setLanguage] = useState(item?.language ?? "en");
  const [topic, setTopic] = useState(item?.topic ?? "");
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!term.trim() || !meaning.trim()) {
      setError("Add a term and its meaning.");
      return;
    }
    setBusy(true);
    setError(null);
    const input = {
      kind,
      term: term.trim(),
      meaning: meaning.trim(),
      example: example.trim(),
      language,
      topic: topic.trim(),
    };
    try {
      if (item) {
        await updateLearnItem(item.id, input);
        toast("Saved.", "success");
      } else {
        const created = await createLearnItem(input);
        toast(created.length ? "Added to your list." : "You already have that one.", "success");
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!item) return;
    setBusy(true);
    try {
      await deleteLearnItem(item.id);
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
      <Field label="Type" htmlFor="wd-kind">
        <Select
          id="wd-kind"
          value={kind}
          className="min-h-11"
          onChange={(e) => setKind(e.target.value as LearnKind)}
        >
          <option value="word">Word</option>
          <option value="phrase">Phrase</option>
          <option value="fact">Fact</option>
        </Select>
      </Field>
      <Field label="Term" htmlFor="wd-term">
        <Input
          id="wd-term"
          value={term}
          maxLength={200}
          className="min-h-11"
          onChange={(e) => setTerm(e.target.value)}
        />
      </Field>
      <Field label="Meaning" htmlFor="wd-meaning">
        <Textarea
          id="wd-meaning"
          value={meaning}
          maxLength={1000}
          onChange={(e) => setMeaning(e.target.value)}
        />
      </Field>
      <Field label="Example" htmlFor="wd-example">
        <Textarea
          id="wd-example"
          value={example}
          maxLength={1000}
          onChange={(e) => setExample(e.target.value)}
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Language" htmlFor="wd-language">
          <Select
            id="wd-language"
            value={language}
            className="min-h-11"
            onChange={(e) => setLanguage(e.target.value)}
          >
            {LANGUAGES.some((l) => l.code === language) ? null : (
              <option value={language}>{language}</option>
            )}
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Topic" htmlFor="wd-topic">
          <Input
            id="wd-topic"
            value={topic}
            maxLength={60}
            className="min-h-11"
            onChange={(e) => setTopic(e.target.value)}
          />
        </Field>
      </div>
      {error ? (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {item ? (
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
            {item ? "Save" : "Add word"}
          </Button>
        </div>
      </div>
      <ConfirmModal
        open={confirmDelete}
        title="Delete this word?"
        message="It will be removed from your list and review."
        confirmLabel="Delete"
        busy={busy}
        onConfirm={() => void remove()}
        onClose={() => setConfirmDelete(false)}
      />
    </form>
  );
}

export function WordDrawer({
  state,
  onClose,
  onSaved,
}: {
  state: WordDrawerState;
  onClose: () => void;
  onSaved: () => void;
}) {
  const key = state ? (state.mode === "edit" ? state.item.id : "add") : "closed";
  return (
    <Drawer
      open={state !== null}
      onClose={onClose}
      title={state?.mode === "edit" ? "Edit word" : "Add word"}
    >
      {state ? <WordForm key={key} state={state} onClose={onClose} onSaved={onSaved} /> : null}
    </Drawer>
  );
}
