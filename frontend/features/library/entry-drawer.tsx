"use client";

import { DriveBadge } from "./drive-badge";
import { useEffect, useState } from "react";
import { Pin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { AssistantMarkdown } from "@/features/chat/assistant-markdown";
import { apiErrorMessage } from "@/lib/api/client";
import { createNote, deleteNote, updateNote, type Mood, type Note } from "@/lib/api/notes";
import { formatEntryDate, sameTags } from "./library-logic";
import { ConfirmModal, TagInput, TOUCH } from "./shared";
import { MoodPicker } from "./mood-picker";

export type DrawerTarget = { mode: "new-note" } | { mode: "edit"; note: Note } | null;

type Props = {
  target: DrawerTarget;
  onClose: () => void;
  /** Called after any successful save or delete so lists reload. */
  onChanged: () => void;
};

const MAX_BODY = 50000;

export function EntryDrawer({ target, onClose, onChanged }: Props) {
  const { toast } = useToast();
  const note = target?.mode === "edit" ? target.note : null;
  const isDiary = note?.kind === "diary";

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [pinned, setPinned] = useState(false);
  const [mood, setMood] = useState<Mood | null>(null);
  const [preview, setPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTitle(note?.title ?? "");
    setBody(note?.body ?? "");
    setTags(note?.tags ?? []);
    setPinned(note?.pinned ?? false);
    setMood(note?.mood ?? null);
    setPreview(false);
    setError(null);
    setConfirmDelete(false);
    setConfirmDiscard(false);
  }, [target, note]);

  const dirty = target
    ? title !== (note?.title ?? "") ||
      body !== (note?.body ?? "") ||
      pinned !== (note?.pinned ?? false) ||
      mood !== (note?.mood ?? null) ||
      !sameTags(tags, note?.tags ?? [])
    : false;

  function requestClose() {
    if (dirty) setConfirmDiscard(true);
    else onClose();
  }

  async function save() {
    if (!body.trim() && !title.trim()) {
      setError("Write something before saving.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (note) {
        await updateNote(note.id, {
          title,
          body,
          tags,
          pinned,
          ...(isDiary ? { mood } : {}),
        });
      } else {
        await createNote({ kind: "note", title, body, tags, pinned });
      }
      toast("Saved.", "success");
      onChanged();
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!note) return;
    setDeleting(true);
    try {
      await deleteNote(note.id);
      toast(isDiary ? "Entry deleted." : "Note deleted.", "success");
      setConfirmDelete(false);
      onChanged();
      onClose();
    } catch (err) {
      setConfirmDelete(false);
      setError(apiErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  }

  const heading = isDiary
    ? note?.entry_date
      ? `Diary, ${formatEntryDate(note.entry_date)}`
      : "Diary entry"
    : note
      ? "Edit note"
      : "New note";

  return (
    <>
      <Drawer open={target !== null} onClose={requestClose} title={heading}>
        <form
          className="flex min-h-full flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <DriveBadge driveUrl={note?.drive_url} withLink />
          {isDiary ? (
            <div>
              <p className="mb-1.5 text-sm font-medium text-[var(--ink)]">Mood</p>
              <MoodPicker value={mood} onChange={setMood} />
            </div>
          ) : (
            <div>
              <label htmlFor="entry-title" className="mb-1.5 block text-sm font-medium">
                Title
              </label>
              <Input
                id="entry-title"
                value={title}
                maxLength={200}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Untitled"
              />
            </div>
          )}

          <div>
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <label htmlFor="entry-body" className="text-sm font-medium text-[var(--ink)]">
                {isDiary ? "Entry" : "Note"}
              </label>
              <div
                role="group"
                aria-label="Editor mode"
                className="inline-flex rounded-[var(--radius)] border border-[var(--border)] p-0.5 text-xs"
              >
                {[
                  { id: false, label: "Write" },
                  { id: true, label: "Preview" },
                ].map((m) => (
                  <button
                    key={m.label}
                    type="button"
                    aria-pressed={preview === m.id}
                    onClick={() => setPreview(m.id)}
                    className={`min-h-9 rounded-md px-3 font-medium focus-visible:outline-2 focus-visible:outline-[var(--accent)] sm:min-h-7 ${
                      preview === m.id
                        ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "text-[var(--muted)]"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
            {preview ? (
              <div
                className="min-h-[220px] rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm"
                aria-live="polite"
              >
                {body.trim() ? (
                  <AssistantMarkdown content={body} />
                ) : (
                  <p className="text-[var(--muted)]">Nothing to preview yet.</p>
                )}
              </div>
            ) : (
              <Textarea
                id="entry-body"
                value={body}
                maxLength={MAX_BODY}
                onChange={(e) => setBody(e.target.value)}
                className="min-h-[220px]"
                placeholder="Markdown is supported."
              />
            )}
          </div>

          <div>
            <label htmlFor="entry-tags" className="mb-1.5 block text-sm font-medium">
              Tags
            </label>
            <TagInput id="entry-tags" tags={tags} onChange={setTags} />
          </div>

          {!isDiary ? (
            <label className="flex min-h-11 items-center gap-2 text-sm sm:min-h-0">
              <input
                type="checkbox"
                checked={pinned}
                onChange={(e) => setPinned(e.target.checked)}
                className="h-4 w-4 accent-[var(--accent)]"
              />
              <Pin className="h-4 w-4 text-[var(--muted)]" aria-hidden />
              Pin to the top
            </label>
          ) : null}

          {error ? (
            <p role="alert" className="text-sm text-[var(--danger)]">
              {error}
            </p>
          ) : null}

          <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
            {note ? (
              <Button
                variant="ghost"
                className={`${TOUCH} text-[var(--danger)]`}
                onClick={() => setConfirmDelete(true)}
              >
                Delete
              </Button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              <Button variant="secondary" className={TOUCH} onClick={requestClose}>
                Cancel
              </Button>
              <Button type="submit" className={TOUCH} loading={saving}>
                Save
              </Button>
            </div>
          </div>
        </form>
      </Drawer>

      <ConfirmModal
        open={confirmDelete}
        title={isDiary ? "Delete this entry?" : "Delete this note?"}
        message="This cannot be undone."
        busy={deleting}
        onConfirm={() => void remove()}
        onClose={() => setConfirmDelete(false)}
      />
      <ConfirmModal
        open={confirmDiscard}
        title="Discard changes?"
        message="You have unsaved changes. They will be lost."
        confirmLabel="Discard"
        onConfirm={() => {
          setConfirmDiscard(false);
          onClose();
        }}
        onClose={() => setConfirmDiscard(false)}
      />
    </>
  );
}
