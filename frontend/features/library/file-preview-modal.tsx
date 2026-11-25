"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import { Button, buttonClassName } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { deleteFile, fileContentUrl, updateFile, type FileItem } from "@/lib/api/files";
import { formatBytes, isImageMime, relativeTime, sameTags } from "./library-logic";
import { DriveBadge } from "./drive-badge";
import { ConfirmModal, TagInput, TOUCH } from "./shared";

type Props = {
  items: FileItem[];
  /** Index into items, or -1 when closed. */
  index: number;
  onIndex: (i: number) => void;
  onClose: () => void;
  onChanged: () => void;
};

export function FilePreviewModal({ items, index, onIndex, onClose, onChanged }: Props) {
  const { toast } = useToast();
  const item = index >= 0 ? (items[index] ?? null) : null;
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setName(item?.name ?? "");
    setDescription(item?.description ?? "");
    setTags(item?.tags ?? []);
    setError(null);
  }, [item]);

  // Arrow keys move between items unless the user is typing in a field.
  useEffect(() => {
    if (!item || confirmDelete) return;
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
      if (e.key === "ArrowLeft" && index > 0) onIndex(index - 1);
      if (e.key === "ArrowRight" && index < items.length - 1) onIndex(index + 1);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [item, index, items.length, onIndex, confirmDelete]);

  if (!item) return null;

  const dirty =
    name !== item.name || description !== item.description || !sameTags(tags, item.tags);

  async function save() {
    if (!item) return;
    if (!name.trim()) {
      setError("A name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateFile(item.id, { name: name.trim(), description, tags });
      toast("Saved.", "success");
      onChanged();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!item) return;
    setDeleting(true);
    try {
      await deleteFile(item.id);
      toast("File deleted.", "success");
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

  const src = fileContentUrl(item);
  return (
    <>
      <Modal open onClose={onClose} title={item.name}>
        <div className="flex max-h-[75dvh] flex-col gap-3 overflow-y-auto">
          {item.kind === "image" && isImageMime(item.mime) ? (
            <div className="flex items-center gap-2">
              <IconButton
                label="Previous"
                disabled={index <= 0}
                onClick={() => onIndex(index - 1)}
                className="h-11 w-11 shrink-0"
              >
                <ChevronLeft className="h-4 w-4" aria-hidden />
              </IconButton>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={src}
                alt={item.name}
                className="max-h-[40dvh] min-w-0 flex-1 rounded-[var(--radius)] object-contain"
              />
              <IconButton
                label="Next"
                disabled={index >= items.length - 1}
                onClick={() => onIndex(index + 1)}
                className="h-11 w-11 shrink-0"
              >
                <ChevronRight className="h-4 w-4" aria-hidden />
              </IconButton>
            </div>
          ) : (
            <p className="text-sm text-[var(--muted)]">No preview for this type. Use Download.</p>
          )}
          <p className="text-xs text-[var(--muted)]">
            {item.mime} · {formatBytes(item.size)} · Added {relativeTime(item.created_at)}
          </p>
          <DriveBadge driveUrl={item.drive_url} withLink />
          <div>
            <label htmlFor="file-name" className="mb-1 block text-sm font-medium">
              Name
            </label>
            <Input id="file-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label htmlFor="file-desc" className="mb-1 block text-sm font-medium">
              Description
            </label>
            <Textarea
              id="file-desc"
              value={description}
              maxLength={500}
              onChange={(e) => setDescription(e.target.value)}
              className="min-h-[72px]"
            />
          </div>
          <div>
            <label htmlFor="file-tags" className="mb-1 block text-sm font-medium">
              Tags
            </label>
            <TagInput id="file-tags" tags={tags} onChange={setTags} />
          </div>
          {error ? (
            <p role="alert" className="text-sm text-[var(--danger)]">
              {error}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button
              variant="ghost"
              className={`${TOUCH} text-[var(--danger)]`}
              onClick={() => setConfirmDelete(true)}
            >
              Delete
            </Button>
            <div className="flex gap-2">
              <a
                href={src}
                download={item.name}
                className={buttonClassName(
                  "secondary",
                  "md",
                  `${TOUCH} focus-visible:outline-2 focus-visible:outline-[var(--accent)]`,
                )}
              >
                <Download className="h-4 w-4" aria-hidden />
                Download
              </a>
              <Button
                className={TOUCH}
                disabled={!dirty}
                loading={saving}
                onClick={() => void save()}
              >
                Save
              </Button>
            </div>
          </div>
        </div>
      </Modal>
      <ConfirmModal
        open={confirmDelete}
        title="Delete this file?"
        message={`"${item.name}" will be removed permanently.`}
        busy={deleting}
        onConfirm={() => void remove()}
        onClose={() => setConfirmDelete(false)}
      />
    </>
  );
}
