"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { apiErrorMessage } from "@/lib/api/client";
import { createMemory, deleteMemory, listMemories, patchMemory } from "@/lib/api/memories";
import type { Memory, MemoryKind } from "@/lib/api/types";

const KINDS: { id: MemoryKind | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "preference", label: "Preference" },
  { id: "fact", label: "Fact" },
  { id: "person", label: "Person" },
  { id: "routine", label: "Routine" },
];

const selectClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)]";

export function MemoryPage() {
  const searchParams = useSearchParams();
  const highlight = searchParams.get("highlight");
  const [items, setItems] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<MemoryKind | "all">("all");
  const [q, setQ] = useState("");
  const [content, setContent] = useState("");
  const [newKind, setNewKind] = useState<MemoryKind>("preference");
  const [formError, setFormError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await listMemories({
        kind: kind === "all" ? undefined : kind,
        q: q.trim() || undefined,
      });
      setItems(next);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [kind, q]);

  useEffect(() => {
    void load();
  }, [load]);

  const sorted = useMemo(() => items, [items]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!content.trim()) {
      setFormError("Enter something to remember.");
      return;
    }
    setCreating(true);
    setFormError(null);
    try {
      await createMemory({ kind: newKind, content: content.trim() });
      setContent("");
      await load();
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function onDelete(id: string) {
    setBusyId(id);
    try {
      await deleteMemory(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function onSaveEdit(id: string) {
    setBusyId(id);
    try {
      const updated = await patchMemory(id, { content: editContent.trim() });
      setItems((prev) => prev.map((item) => (item.id === id ? updated : item)));
      setEditingId(null);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Memory</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What AURA knows about you
        </h1>
        <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
          Saved only when you ask or confirm a Save chip. Delete anytime.
        </p>
      </header>

      <form
        onSubmit={onCreate}
        className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
      >
        <Field label="Add a memory" htmlFor="memory-content">
          <Input
            id="memory-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="e.g. Prefers morning meetings"
          />
        </Field>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-[var(--muted)]">Kind</span>
            <select
              className={selectClass}
              value={newKind}
              onChange={(e) => setNewKind(e.target.value as MemoryKind)}
            >
              {KINDS.filter((k) => k.id !== "all").map((k) => (
                <option key={k.id} value={k.id}>
                  {k.label}
                </option>
              ))}
            </select>
          </label>
          <Button type="submit" disabled={creating}>
            {creating ? "Saving…" : "Add"}
          </Button>
        </div>
        {formError ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {formError}
          </p>
        ) : null}
      </form>

      <div className="flex flex-wrap items-center gap-2">
        {KINDS.map((item) => (
          <Button
            key={item.id}
            size="sm"
            variant={kind === item.id ? "primary" : "secondary"}
            onClick={() => setKind(item.id)}
          >
            {item.label}
          </Button>
        ))}
        <Input
          className="ml-auto max-w-xs"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search memories"
          aria-label="Search memories"
        />
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Spinner size="sm" /> Loading memories…
        </div>
      ) : null}

      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}

      {!loading && sorted.length === 0 ? (
        <EmptyState
          title="No memories yet"
          description="Ask AURA to remember something, or add one above. Confirmed Save chips also appear here."
        />
      ) : null}

      <ul className="flex flex-col gap-3">
        {sorted.map((item) => {
          const active = highlight === item.id;
          return (
            <li
              key={item.id}
              id={`memory-${item.id}`}
              className={`rounded-[var(--radius)] border bg-[var(--surface)] px-4 py-3 ${
                active ? "border-[var(--accent)]" : "border-[var(--border)]"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="neutral">{item.kind}</Badge>
                {item.last_used_at ? (
                  <span className="text-xs text-[var(--muted)]">
                    Last used {new Date(item.last_used_at).toLocaleString()}
                  </span>
                ) : null}
              </div>
              {editingId === item.id ? (
                <div className="mt-2 flex flex-col gap-2">
                  <Input value={editContent} onChange={(e) => setEditContent(e.target.value)} />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={busyId === item.id}
                      onClick={() => void onSaveEdit(item.id)}
                    >
                      Save
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => setEditingId(null)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-sm text-[var(--ink)]">{item.content}</p>
              )}
              {editingId !== item.id ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setEditingId(item.id);
                      setEditContent(item.content);
                    }}
                  >
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busyId === item.id}
                    onClick={() => void onDelete(item.id)}
                  >
                    Delete
                  </Button>
                  {item.source_run_id ? <Linkish runId={item.source_run_id} /> : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Linkish({ runId }: { runId: string }) {
  return (
    <span className="self-center text-xs text-[var(--muted)]">From run {runId.slice(0, 8)}…</span>
  );
}
