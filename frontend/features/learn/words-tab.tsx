"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Plus, Search } from "lucide-react";
import { Button, buttonClassName } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiErrorMessage } from "@/lib/api/client";
import { listLearnItems, listLearnTopics, type LearnItem } from "@/lib/api/learn";
import { LevelDots } from "./level-dots";
import { formatDue, previewText } from "./learn-logic";
import { WordDrawer, type WordDrawerState } from "./word-drawer";

const columns: Column<LearnItem>[] = [
  {
    id: "term",
    header: "Term",
    cell: (r) => <span className="font-medium text-[var(--ink)]">{r.term}</span>,
    sortValue: (r) => r.term.toLowerCase(),
  },
  {
    id: "meaning",
    header: "Meaning",
    cell: (r) => previewText(r.meaning, 90),
    sortValue: (r) => r.meaning.toLowerCase(),
  },
  {
    id: "example",
    header: "Example",
    cell: (r) => <span className="text-[var(--muted)]">{previewText(r.example, 90)}</span>,
    hideOnMobile: true,
  },
  {
    id: "topic",
    header: "Topic",
    cell: (r) => r.topic || "None",
    sortValue: (r) => r.topic.toLowerCase(),
    hideOnMobile: true,
  },
  {
    id: "box",
    header: "Level",
    cell: (r) => <LevelDots box={r.box} />,
    sortValue: (r) => r.box,
  },
  {
    id: "due",
    header: "Due",
    cell: (r) => formatDue(r.next_review_at),
    sortValue: (r) => Date.parse(r.next_review_at) || 0,
    hideOnMobile: true,
  },
];

export function WordsTab() {
  const [items, setItems] = useState<LearnItem[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [topic, setTopic] = useState("");
  const [drawer, setDrawer] = useState<WordDrawerState>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, t] = await Promise.all([
        listLearnItems({ q: q.trim() || undefined, topic: topic || undefined }),
        listLearnTopics().catch(() => [] as string[]),
      ]);
      setItems(list);
      setTopics(t);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [q, topic]);

  useEffect(() => {
    const t = setTimeout(() => void load(), q ? 250 : 0);
    return () => clearTimeout(t);
  }, [load, q]);

  const dueCount = useMemo(
    () => items.filter((i) => Date.parse(i.next_review_at) <= Date.now()).length,
    [items],
  );
  const filtered = Boolean(q.trim() || topic);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="relative min-w-48 flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--muted)]"
            aria-hidden
          />
          <Input
            type="search"
            aria-label="Search words"
            placeholder="Search words"
            value={q}
            className="min-h-11 pl-9"
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <Select
          aria-label="Filter by topic"
          value={topic}
          className="min-h-11"
          onChange={(e) => setTopic(e.target.value)}
        >
          <option value="">All topics</option>
          {topics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
        {dueCount > 0 ? (
          <Link href="/learn?tab=today" className={buttonClassName("secondary", "md", "min-h-11")}>
            Review these ({dueCount})
          </Link>
        ) : null}
        <Button className="min-h-11" onClick={() => setDrawer({ mode: "add" })}>
          <Plus className="h-4 w-4" aria-hidden />
          Add word
        </Button>
      </div>
      <Card flush>
        <DataTable
          label="Words"
          columns={columns}
          rows={items}
          rowKey={(r) => r.id}
          loading={loading}
          error={error}
          onRetry={() => void load()}
          empty={
            filtered
              ? { title: "No matches", description: "Try a different search or topic." }
              : {
                  title: "No words yet",
                  description: "Press Add word, or ask AURA from the Today tab to teach you some.",
                }
          }
          onRowClick={(r) => setDrawer({ mode: "edit", item: r })}
          selectedKey={drawer?.mode === "edit" ? drawer.item.id : null}
        />
      </Card>
      <WordDrawer state={drawer} onClose={() => setDrawer(null)} onSaved={() => void load()} />
    </div>
  );
}
