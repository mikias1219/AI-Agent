"use client";

import { useEffect, useMemo, useState } from "react";
import { BookOpen, Flame, PenLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { KpiCard } from "@/components/ui/kpi-card";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusChip } from "@/components/ui/status-chip";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { ApiError, apiErrorMessage } from "@/lib/api/client";
import {
  createNote,
  getNoteStats,
  listNotes,
  updateNote,
  type Mood,
  type Note,
} from "@/lib/api/notes";
import { EntryDrawer, type DrawerTarget } from "./entry-drawer";
import {
  askCompassHref,
  formatEntryDate,
  groupDiaryByMonth,
  MOODS,
  previewText,
  todayIso,
} from "./library-logic";
import { MoodPicker } from "./mood-picker";
import { DriveBadge } from "./drive-badge";
import { AskCompassLink, ErrorBlock, ListSkeleton, TOUCH, useLoad } from "./shared";

const PAGE_SIZE = 20;

export function DiaryTab() {
  const { toast } = useToast();
  const [page, setPage] = useState(1);
  const [target, setTarget] = useState<DrawerTarget>(null);

  const stats = useLoad(() => getNoteStats(), []);
  const list = useLoad(
    () => listNotes({ kind: "diary", limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
    [page],
  );
  // Today's entry is always on the first page (newest first).
  const first = useLoad(() => listNotes({ kind: "diary", limit: 3, offset: 0 }), []);

  const today = todayIso();
  const todayEntry = useMemo(
    () => first.data?.find((e) => e.entry_date === today) ?? null,
    [first.data, today],
  );

  const [body, setBody] = useState("");
  const [mood, setMood] = useState<Mood | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Load today's entry into the composer once known.
  useEffect(() => {
    if (todayEntry && editingId !== todayEntry.id) {
      setEditingId(todayEntry.id);
      setBody(todayEntry.body);
      setMood(todayEntry.mood);
    }
  }, [todayEntry, editingId]);

  // If the entry being edited was deleted elsewhere (drawer), reset the composer.
  useEffect(() => {
    if (first.data && editingId && !first.data.some((e) => e.id === editingId)) {
      setEditingId(null);
      setBody("");
      setMood(null);
    }
  }, [first.data, editingId]);

  function reloadAll() {
    stats.reload();
    list.reload();
    first.reload();
  }

  async function save() {
    if (!body.trim()) {
      setFormError("Write a few words first.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      if (editingId) {
        await updateNote(editingId, { body, mood });
      } else {
        try {
          const created = await createNote({ kind: "diary", body, mood });
          setEditingId(created.id);
        } catch (err) {
          if (err instanceof ApiError && err.status === 409) {
            // Today's entry exists but was not loaded yet. Load it instead of overwriting.
            const latest = await listNotes({ kind: "diary", limit: 3, offset: 0 });
            const existing = latest.find((e) => e.entry_date === today) ?? latest[0];
            if (existing) {
              setEditingId(existing.id);
              setBody(existing.body);
              setMood(existing.mood);
            }
            reloadAll();
            setFormError("Today already has an entry. It is loaded above, so edit it and save.");
            return;
          }
          throw err;
        }
      }
      toast("Diary saved.", "success");
      reloadAll();
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const groups = useMemo(() => groupDiaryByMonth(list.data ?? []), [list.data]);
  const total = stats.data?.diary_entries ?? list.data?.length ?? 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        {stats.loading && !stats.data ? (
          <>
            <Skeleton heightClass="h-28" />
            <Skeleton heightClass="h-28" />
          </>
        ) : stats.error ? (
          <div className="col-span-2">
            <ErrorBlock message={`Could not load stats: ${stats.error}`} onRetry={stats.reload} />
          </div>
        ) : (
          <>
            <KpiCard
              label="Day streak"
              value={stats.data?.diary_streak_days ?? 0}
              icon={Flame}
              hint={stats.data?.wrote_diary_today ? "Written today" : "Not written today"}
            />
            <KpiCard label="Entries" value={stats.data?.diary_entries ?? 0} icon={BookOpen} />
          </>
        )}
      </div>

      <section
        aria-labelledby="diary-today"
        className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
      >
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 id="diary-today" className="text-[length:var(--text-title)] font-semibold">
            Today
            <span className="ml-2 text-sm font-normal text-[var(--muted)]">
              {formatEntryDate(today)}
            </span>
          </h2>
          <div className="flex items-center gap-2">
            <AskCompassLink href={askCompassHref("Add to my diary: ")} label="Ask Compass" />
            <Button
              variant="secondary"
              className={TOUCH}
              onClick={() => document.getElementById("diary-today-body")?.focus()}
            >
              <PenLine className="h-4 w-4" aria-hidden />
              Write today
            </Button>
          </div>
        </div>
        <div className="flex flex-col gap-3">
          <MoodPicker value={mood} onChange={setMood} />
          <label htmlFor="diary-today-body" className="sr-only">
            Today&apos;s diary entry
          </label>
          <Textarea
            id="diary-today-body"
            value={body}
            maxLength={50000}
            onChange={(e) => setBody(e.target.value)}
            className="min-h-[140px]"
            placeholder="How was your day?"
          />
          {formError ? (
            <p role="alert" className="text-sm text-[var(--danger)]">
              {formError}
            </p>
          ) : null}
          <div className="flex justify-end">
            <Button className={TOUCH} loading={saving} onClick={() => void save()}>
              {editingId ? "Save changes" : "Save"}
            </Button>
          </div>
        </div>
      </section>

      {list.error ? (
        <ErrorBlock message={`Could not load entries: ${list.error}`} onRetry={list.reload} />
      ) : list.loading && !list.data ? (
        <ListSkeleton count={3} />
      ) : groups.length === 0 ? (
        <EmptyState
          compact
          title="No entries yet"
          description="Your first entry will appear here once you save it above."
          action={
            <AskCompassLink
              href={askCompassHref("Help me write my first diary entry")}
              label="Ask Compass"
            />
          }
        />
      ) : (
        <div className="flex flex-col gap-5" aria-busy={list.loading}>
          {groups.map((g) => (
            <section key={g.key} aria-label={g.label}>
              <h3 className="mb-2 text-sm font-semibold text-[var(--muted)]">{g.label}</h3>
              <ul className="flex flex-col gap-2">
                {g.items.map((entry) => (
                  <DiaryRow
                    key={entry.id}
                    entry={entry}
                    onOpen={() => setTarget({ mode: "edit", note: entry })}
                  />
                ))}
              </ul>
            </section>
          ))}
          {total > PAGE_SIZE ? (
            <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
          ) : null}
        </div>
      )}

      <EntryDrawer target={target} onClose={() => setTarget(null)} onChanged={reloadAll} />
    </div>
  );
}

function DiaryRow({ entry, onOpen }: { entry: Note; onOpen: () => void }) {
  const mood = MOODS.find((m) => m.value === entry.mood);
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex min-h-11 w-full flex-col gap-1 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left transition hover:border-[var(--accent)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
      >
        <span className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-[var(--ink)]">
            {entry.entry_date ? formatEntryDate(entry.entry_date) : "Entry"}
          </span>
          {mood ? <StatusChip tone="accent">{mood.label}</StatusChip> : null}
        </span>
        <span className="line-clamp-2 text-sm text-[var(--muted)]">
          {previewText(entry.body) || "No text"}
        </span>
        <DriveBadge driveUrl={entry.drive_url} />
      </button>
    </li>
  );
}
