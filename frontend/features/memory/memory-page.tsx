"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { SkeletonRows } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/lib/api/client";
import { listAgentSkills, type AgentSkill } from "@/lib/api/agent-skills";
import {
  confirmMemoryProposal,
  createMemory,
  deleteMemory,
  dismissMemoryProposal,
  forgetAllMemories,
  issueForgetToken,
  listMemories,
  listMemoryProposals,
  patchMemory,
} from "@/lib/api/memories";
import type { Memory, MemoryKind, MemoryProposal } from "@/lib/api/types";

const KIND_ORDER: { id: MemoryKind; label: string }[] = [
  { id: "fact", label: "Facts" },
  { id: "person", label: "People" },
  { id: "preference", label: "Preferences" },
  { id: "routine", label: "Routines" },
];

const KIND_SINGULAR: Record<MemoryKind, string> = {
  fact: "Fact",
  person: "Person",
  preference: "Preference",
  routine: "Routine",
};

type MemoryTab = "saved" | "proposed";

export type MemoryPageProps = {
  embedded?: boolean;
};

/** "Used 3 days ago" hint, or a plain "Not used yet". */
export function usedHint(iso: string | null, now: number = Date.now()): string {
  if (!iso) return "Not used yet";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "Not used yet";
  const minutes = Math.max(0, Math.round((now - then) / 60000));
  if (minutes < 1) return "Used just now";
  if (minutes < 60) return `Used ${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `Used ${hours} h ago`;
  const days = Math.round(hours / 24);
  return `Used ${days} ${days === 1 ? "day" : "days"} ago`;
}

type DrawerState = { mode: "add" } | { mode: "edit"; memory: Memory } | null;

export function MemoryPage(_props: MemoryPageProps = {}) {
  const searchParams = useSearchParams();
  const highlight = searchParams.get("highlight");
  const [items, setItems] = useState<Memory[]>([]);
  const [proposals, setProposals] = useState<MemoryProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<MemoryTab>(() =>
    searchParams.get("tab") === "proposed" ? "proposed" : "saved",
  );
  const [q, setQ] = useState("");
  const [drawer, setDrawer] = useState<DrawerState>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [skills, setSkills] = useState<AgentSkill[] | null>(null);
  const [highlightHandled, setHighlightHandled] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const pending = await listMemoryProposals().catch(() => [] as MemoryProposal[]);
      setProposals(pending);
      setItems(await listMemories({ q: q.trim() || undefined }));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => {
    void load();
  }, [load]);

  // Deep link from a "Used memory" chip opens that memory once it has loaded.
  useEffect(() => {
    if (!highlight || highlightHandled || loading) return;
    const match = items.find((row) => row.id === highlight);
    if (match) setDrawer({ mode: "edit", memory: match });
    setHighlightHandled(true);
  }, [highlight, highlightHandled, loading, items]);

  const groups = useMemo(
    () =>
      KIND_ORDER.map((kind) => ({
        ...kind,
        rows: items.filter((row) => row.kind === kind.id),
      })).filter((group) => group.rows.length > 0),
    [items],
  );

  async function onProposal(id: string, action: "confirm" | "dismiss") {
    setBusyId(id);
    try {
      if (action === "confirm") {
        await confirmMemoryProposal(id);
        setItems(await listMemories({ q: q.trim() || undefined }));
      } else {
        await dismissMemoryProposal(id);
      }
      setProposals((prev) => prev.filter((row) => row.id !== id));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function loadSkills() {
    if (skills) return;
    try {
      setSkills(await listAgentSkills());
    } catch {
      setSkills([]);
    }
  }

  const columns: Column<Memory>[] = [
    {
      id: "content",
      header: "Memory",
      sortValue: (row) => row.content.toLowerCase(),
      cell: (row) => (
        <span className="block min-w-0 text-[var(--ink)]">
          {row.content}
          <span className="mt-0.5 block text-[length:var(--text-caption)] text-[var(--muted)] md:hidden">
            {usedHint(row.last_used_at)}
          </span>
        </span>
      ),
    },
    {
      id: "used",
      header: "Used",
      width: "w-40",
      hideOnMobile: true,
      sortValue: (row) => (row.last_used_at ? new Date(row.last_used_at).getTime() : 0),
      cell: (row) => (
        <span className="text-[length:var(--text-small)] text-[var(--muted)]">
          {usedHint(row.last_used_at)}
        </span>
      ),
    },
    {
      id: "edit",
      header: "Edit",
      width: "w-24",
      align: "right",
      cell: (row) => (
        <Button
          size="sm"
          variant="secondary"
          className="min-h-11 md:min-h-0"
          aria-label={`Edit ${row.content}`}
          onClick={(event) => {
            event.stopPropagation();
            setDrawer({ mode: "edit", memory: row });
          }}
        >
          Edit
        </Button>
      ),
    },
  ];

  const proposedLabel = proposals.length > 0 ? `Proposed (${proposals.length})` : "Proposed";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Tabs
          aria-label="Memory view"
          items={[
            { id: "saved", label: "Saved" },
            { id: "proposed", label: proposedLabel },
          ]}
          value={tab}
          onChange={(id) => setTab(id as MemoryTab)}
        />
        {tab === "saved" ? (
          <Input
            className="min-h-11 flex-1 sm:ml-2"
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search memories"
            aria-label="Search memories"
          />
        ) : (
          <span className="flex-1" />
        )}
        <Button className="min-h-11 sm:min-h-0" onClick={() => setDrawer({ mode: "add" })}>
          Add memory
        </Button>
      </div>

      {error ? (
        <Banner tone="danger" role="alert">
          <div className="flex flex-wrap items-center gap-3">
            <span>Could not load memory: {error}</span>
            <Button size="sm" variant="secondary" onClick={() => void load()}>
              Try again
            </Button>
          </div>
        </Banner>
      ) : null}

      {loading ? <SkeletonRows count={4} /> : null}

      {!loading && !error && tab === "proposed" ? (
        proposals.length === 0 ? (
          <EmptyState
            title="No proposals waiting"
            description="When AURA suggests remembering something in Chat, it waits here until you save or dismiss it. Nothing is stored until you confirm."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {proposals.map((item, index) => (
              <li key={item.id ?? index}>
                <Card
                  title={item.content}
                  description={`${KIND_SINGULAR[item.kind]} · ${item.source || "From AURA"}`}
                >
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      className="min-h-11 sm:min-h-0"
                      disabled={!item.id || busyId === item.id}
                      onClick={() => item.id && void onProposal(item.id, "confirm")}
                    >
                      Save
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="min-h-11 sm:min-h-0"
                      disabled={!item.id || busyId === item.id}
                      onClick={() => item.id && void onProposal(item.id, "dismiss")}
                    >
                      Dismiss
                    </Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )
      ) : null}

      {!loading && !error && tab === "saved" ? (
        groups.length === 0 ? (
          <EmptyState
            title={q.trim() ? "No matching memories" : "AURA has not saved anything yet"}
            description={
              q.trim()
                ? "Try a different word, or clear the search."
                : "Memories are facts, people and preferences AURA uses to help you. Nothing is stored until you confirm it."
            }
            action={
              q.trim() ? (
                <Button variant="secondary" onClick={() => setQ("")}>
                  Clear search
                </Button>
              ) : (
                <Button onClick={() => setDrawer({ mode: "add" })}>Add a memory</Button>
              )
            }
          />
        ) : (
          groups.map((group) => (
            <Card
              key={group.id}
              id={`memory-group-${group.id}`}
              title={`${group.label} (${group.rows.length})`}
              flush
            >
              <DataTable
                label={group.label}
                columns={columns}
                rows={group.rows}
                rowKey={(row) => row.id}
                pageSize={10}
                selectedKey={drawer?.mode === "edit" ? drawer.memory.id : (highlight ?? null)}
                onRowClick={(row) => setDrawer({ mode: "edit", memory: row })}
              />
            </Card>
          ))
        )
      ) : null}

      <details
        className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2"
        onToggle={(event) => {
          if (event.currentTarget.open) void loadSkills();
        }}
      >
        <summary className="min-h-11 cursor-pointer py-2.5 text-sm font-medium text-[var(--ink)]">
          Built-in skills
        </summary>
        <div className="pb-3">
          {skills === null ? (
            <p className="text-sm text-[var(--muted)]">Loading…</p>
          ) : skills.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              No built-in skills were found on the server.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {skills.map((skill) => (
                <li key={skill.name}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="accent">{skill.workflow || "Skill"}</Badge>
                    <span className="text-sm font-medium text-[var(--ink)]">{skill.name}</span>
                  </div>
                  <p className="mt-1 text-sm text-[var(--muted)]">{skill.description}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>

      <ForgetEverything
        disabled={items.length === 0 && !loading}
        onForgotten={() => {
          setItems([]);
          void load();
        }}
      />

      <Drawer
        open={drawer !== null}
        onClose={() => setDrawer(null)}
        title={drawer?.mode === "edit" ? "Edit memory" : "Add memory"}
      >
        {drawer ? (
          <MemoryForm
            key={drawer.mode === "edit" ? drawer.memory.id : "new"}
            memory={drawer.mode === "edit" ? drawer.memory : null}
            onClose={() => setDrawer(null)}
            onSaved={(saved, isNew) => {
              setItems((prev) =>
                isNew ? [saved, ...prev] : prev.map((row) => (row.id === saved.id ? saved : row)),
              );
              setDrawer(null);
            }}
            onDeleted={(id) => {
              setItems((prev) => prev.filter((row) => row.id !== id));
              setDrawer(null);
            }}
          />
        ) : null}
      </Drawer>
    </div>
  );
}

function MemoryForm({
  memory,
  onClose,
  onSaved,
  onDeleted,
}: {
  memory: Memory | null;
  onClose: () => void;
  onSaved: (memory: Memory, isNew: boolean) => void;
  onDeleted: (id: string) => void;
}) {
  const [content, setContent] = useState(memory?.content ?? "");
  const [kind, setKind] = useState<MemoryKind>(memory?.kind ?? "fact");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!content.trim()) {
      setError("Enter something to remember.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (memory) {
        const updated = await patchMemory(memory.id, { content: content.trim(), kind });
        onSaved(updated, false);
      } else {
        onSaved(await createMemory({ kind, content: content.trim() }), true);
      }
    } catch (err) {
      setError(apiErrorMessage(err));
      setBusy(false);
    }
  }

  async function onDelete() {
    if (!memory) return;
    setBusy(true);
    setError(null);
    try {
      await deleteMemory(memory.id);
      onDeleted(memory.id);
    } catch (err) {
      setError(apiErrorMessage(err));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <Field label="What should AURA remember?" htmlFor="memory-content">
        <Textarea
          id="memory-content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="e.g. Prefers morning meetings"
          rows={4}
        />
      </Field>
      <Field label="Type" htmlFor="memory-kind">
        <Select
          id="memory-kind"
          className="min-h-11"
          value={kind}
          onChange={(e) => setKind(e.target.value as MemoryKind)}
        >
          {KIND_ORDER.map((k) => (
            <option key={k.id} value={k.id}>
              {KIND_SINGULAR[k.id]}
            </option>
          ))}
        </Select>
      </Field>
      {memory ? (
        <p className="text-[length:var(--text-caption)] text-[var(--muted)]">
          {usedHint(memory.last_used_at)}
          {memory.source_run_id ? ` · From run ${memory.source_run_id.slice(0, 8)}` : ""}
        </p>
      ) : null}
      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" className="min-h-11" loading={busy}>
          Save
        </Button>
        <Button type="button" variant="secondary" className="min-h-11" onClick={onClose}>
          Cancel
        </Button>
        {memory ? (
          <Button
            type="button"
            variant="ghost"
            className="ml-auto min-h-11 text-[var(--danger)]"
            disabled={busy}
            onClick={() => void onDelete()}
          >
            Delete this memory
          </Button>
        ) : null}
      </div>
    </form>
  );
}

function ForgetEverything({
  disabled,
  onForgotten,
}: {
  disabled: boolean;
  onForgotten: () => void;
}) {
  const [challenge, setChallenge] = useState<{ token: string; phrase: string } | null>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<number | null>(null);

  async function prepare() {
    setError(null);
    try {
      const issued = await issueForgetToken();
      setChallenge({ token: issued.token, phrase: issued.confirm_phrase });
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function forget() {
    if (!challenge) return;
    setBusy(true);
    setError(null);
    try {
      const result = await forgetAllMemories({
        token: challenge.token,
        confirm_phrase: typed.trim(),
      });
      setDone(result.deleted);
      setChallenge(null);
      setTyped("");
      onForgotten();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <details
      className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2"
      onToggle={(event) => {
        if (event.currentTarget.open && !challenge) void prepare();
      }}
    >
      <summary className="min-h-11 cursor-pointer py-2.5 text-sm font-medium text-[var(--danger)]">
        Forget everything
      </summary>
      <div className="flex flex-col gap-3 pb-3">
        <p className="text-sm text-[var(--muted)]">
          This permanently deletes every saved memory. It cannot be undone.
        </p>
        {done !== null ? (
          <p className="text-sm text-[var(--ink)]" role="status">
            Forgot {done} {done === 1 ? "memory" : "memories"}.
          </p>
        ) : null}
        {challenge ? (
          <Field label={`Type "${challenge.phrase}" to confirm`} htmlFor="forget-phrase">
            <Input
              id="forget-phrase"
              className="min-h-11"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoComplete="off"
            />
          </Field>
        ) : null}
        {error ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}
        <div>
          <Button
            variant="danger"
            className="min-h-11 sm:min-h-0"
            loading={busy}
            disabled={disabled || !challenge || typed.trim() !== challenge.phrase}
            onClick={() => void forget()}
          >
            Forget everything
          </Button>
        </div>
      </div>
    </details>
  );
}
