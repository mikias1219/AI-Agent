"use client";

import { useEffect, useMemo, useState } from "react";
import { Pin, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { listNotes, type Note } from "@/lib/api/notes";
import { DriveBadge } from "./drive-badge";
import { EntryDrawer, type DrawerTarget } from "./entry-drawer";
import { askAuraHref, previewText, relativeTime } from "./library-logic";
import { AskAuraLink, ErrorBlock, ListSkeleton, TagChips, TOUCH, useLoad } from "./shared";

export function NotesTab() {
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [tag, setTag] = useState("");
  const [known, setKnown] = useState<string[]>([]);
  const [target, setTarget] = useState<DrawerTarget>(null);

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(search.trim()), 250);
    return () => window.clearTimeout(t);
  }, [search]);

  const { data, loading, error, reload } = useLoad(
    () => listNotes({ kind: "note", q: debounced, tag, limit: 200 }),
    [debounced, tag],
  );

  useEffect(() => {
    if (!data) return;
    setKnown((prev) => Array.from(new Set([...prev, ...data.flatMap((n) => n.tags)])).sort());
  }, [data]);

  const notes = useMemo(
    () =>
      data
        ? [...data].sort((a, b) => Number(b.pinned) - Number(a.pinned)) // stable: server order within groups
        : [],
    [data],
  );
  const filtering = debounced !== "" || tag !== "";
  const askPrompt = debounced ? `Find my notes about ${debounced}` : "Find my notes about ";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-0 flex-1 basis-48">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--muted)]"
            aria-hidden
          />
          <Input
            type="search"
            aria-label="Search notes"
            placeholder="Search notes"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="min-h-11 pl-9 sm:min-h-0"
          />
        </div>
        <Select
          aria-label="Filter by tag"
          value={tag}
          onChange={(e) => setTag(e.target.value)}
          className="min-h-11 max-w-full sm:min-h-0"
        >
          <option value="">All tags</option>
          {known.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
        <AskAuraLink href={askAuraHref(askPrompt)} label="Ask AURA" />
        <Button className={TOUCH} onClick={() => setTarget({ mode: "new-note" })}>
          <Plus className="h-4 w-4" aria-hidden />
          New note
        </Button>
      </div>

      {error ? (
        <ErrorBlock message={`Could not load notes: ${error}`} onRetry={reload} />
      ) : loading && !data ? (
        <ListSkeleton />
      ) : notes.length === 0 ? (
        filtering ? (
          <EmptyState
            compact
            title="No notes match"
            description="Try a different word or clear the tag filter."
            action={
              <Button
                variant="secondary"
                className={TOUCH}
                onClick={() => {
                  setSearch("");
                  setTag("");
                }}
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          <EmptyState
            title="Nothing here yet."
            description="Write your first note, or ask AURA to remember something."
            action={
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button className={TOUCH} onClick={() => setTarget({ mode: "new-note" })}>
                  New note
                </Button>
                <AskAuraLink href={askAuraHref("Remember that ")} label="Ask AURA to remember" />
              </div>
            }
          />
        )
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2" aria-busy={loading}>
          {notes.map((n) => (
            <NoteCard key={n.id} note={n} onOpen={() => setTarget({ mode: "edit", note: n })} />
          ))}
        </ul>
      )}

      <EntryDrawer target={target} onClose={() => setTarget(null)} onChanged={reload} />
    </div>
  );
}

function NoteCard({ note, onOpen }: { note: Note; onOpen: () => void }) {
  return (
    <li className="min-w-0">
      <button
        type="button"
        onClick={onOpen}
        className="flex h-full min-h-11 w-full flex-col gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 text-left transition hover:border-[var(--accent)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
      >
        <span className="flex items-start justify-between gap-2">
          <span className="min-w-0 truncate text-[length:var(--text-body)] font-semibold text-[var(--ink)]">
            {note.title || "Untitled"}
          </span>
          {note.pinned ? (
            <Pin className="h-4 w-4 shrink-0 text-[var(--accent)]" aria-label="Pinned" />
          ) : null}
        </span>
        <span className="line-clamp-2 text-sm text-[var(--muted)]">
          {previewText(note.body) || "No text"}
        </span>
        <TagChips tags={note.tags} />
        <DriveBadge driveUrl={note.drive_url} />
        <span className="mt-auto text-xs text-[var(--muted)]">{relativeTime(note.updated_at)}</span>
      </button>
    </li>
  );
}
