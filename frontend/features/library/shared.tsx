"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { askModuleAgent } from "@/features/module-agent/module-agent";
import { Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { apiErrorMessage } from "@/lib/api/client";
import { addTags, MAX_TAGS } from "./library-logic";

export const TOUCH = "min-h-11 sm:min-h-0";

export type LoadState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
};

/** Loads data via `fn` whenever `deps` change. Stale responses are ignored. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[]): LoadState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    fnRef
      .current()
      .then((result) => {
        if (live) setData(result);
      })
      .catch((err) => {
        if (live) setError(apiErrorMessage(err));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  return { data, loading, error, reload };
}

/** Opens the Notes agent on this page with `prompt` ready to finish and send. */
export function AskCompassLink({ prompt, label }: { prompt: string; label: string }) {
  return (
    <button
      type="button"
      onClick={() => askModuleAgent({ module: "library", text: prompt, send: false })}
      className="inline-flex min-h-11 items-center gap-1.5 rounded-[var(--radius)] px-2 text-sm font-medium text-[var(--accent)] hover:underline focus-visible:outline-2 focus-visible:outline-[var(--accent)] sm:min-h-0"
    >
      <Sparkles className="h-4 w-4" aria-hidden />
      {label}
    </button>
  );
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-6 text-sm"
    >
      <span className="text-[var(--danger)]">{message}</span>
      <Button size="sm" variant="secondary" className={TOUCH} onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}

export function TagChips({ tags }: { tags: string[] }) {
  if (tags.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-1" aria-label="Tags">
      {tags.map((t) => (
        <li
          key={t}
          className="rounded-full border border-[var(--border)] bg-[var(--canvas)] px-2 py-0.5 text-xs text-[var(--muted)]"
        >
          {t}
        </li>
      ))}
    </ul>
  );
}

export function TagInput({
  tags,
  onChange,
  id,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
  id: string;
}) {
  const [draft, setDraft] = useState("");

  function commit(raw: string) {
    if (!raw.trim()) return;
    onChange(addTags(tags, raw));
    setDraft("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit(draft);
    } else if (e.key === "Backspace" && draft === "" && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  }

  const full = tags.length >= MAX_TAGS;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1.5 focus-within:border-[var(--accent)] focus-within:ring-2 focus-within:ring-[var(--accent-soft)]">
        {tags.map((t) => (
          <span
            key={t}
            className="inline-flex items-center gap-1 rounded-full bg-[var(--accent-soft)] py-0.5 pr-1 pl-2.5 text-xs font-medium text-[var(--accent)]"
          >
            {t}
            <button
              type="button"
              aria-label={`Remove tag ${t}`}
              className="inline-flex h-5 w-5 items-center justify-center rounded-full hover:bg-[var(--surface)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
              onClick={() => onChange(tags.filter((x) => x !== t))}
            >
              <X className="h-3 w-3" aria-hidden />
            </button>
          </span>
        ))}
        <input
          id={id}
          value={draft}
          disabled={full}
          onChange={(e) => {
            const v = e.target.value;
            if (v.includes(",")) commit(v);
            else setDraft(v);
          }}
          onKeyDown={onKeyDown}
          onBlur={() => commit(draft)}
          placeholder={full ? "Tag limit reached" : tags.length ? "" : "Add a tag"}
          className="min-h-8 min-w-0 flex-1 bg-transparent px-1 text-sm text-[var(--ink)] placeholder:text-[var(--muted)] focus:outline-none"
        />
      </div>
      <p className="mt-1 text-xs text-[var(--muted)]">
        Press Enter or comma to add. Up to {MAX_TAGS} tags.
      </p>
    </div>
  );
}

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Delete",
  busy,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-[var(--ink)]">{message}</p>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" className={TOUCH} onClick={onClose}>
          Cancel
        </Button>
        <Button variant="danger" className={TOUCH} loading={busy} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

export function ListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          aria-hidden
          className="h-20 animate-pulse rounded-[var(--radius)] bg-[color-mix(in_srgb,var(--muted)_18%,var(--surface))]"
        />
      ))}
    </div>
  );
}
