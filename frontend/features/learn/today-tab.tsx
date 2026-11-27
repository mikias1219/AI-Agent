"use client";

import { useCallback, useEffect, useState } from "react";
import { Flame, GraduationCap, Timer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { askModuleAgent } from "@/features/module-agent/module-agent";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { KpiCard } from "@/components/ui/kpi-card";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  getLearnStats,
  listLearnItems,
  reviewLearnItem,
  type LearnItem,
  type LearnStats,
  type ReviewResult,
} from "@/lib/api/learn";
import {
  LANGUAGES,
  WORD_COUNTS,
  buildWordsPrompt,
  formatDue,
  languageLabel,
  newWordsContext,
  nextDueIso,
  orderReviewQueue,
  reviewKeyAction,
} from "./learn-logic";
import { CardSkeleton, ErrorBlock } from "./states";

function GetWordsCard() {
  const [count, setCount] = useState<number>(5);
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState("en");
  const [busy, setBusy] = useState(false);

  async function getWords() {
    setBusy(true);
    try {
      // Send every saved word so the Learn agent only picks words you don't have yet.
      const saved = await listLearnItems({}).catch(() => [] as LearnItem[]);
      askModuleAgent({
        module: "learn",
        text: buildWordsPrompt(count, topic, languageLabel(language)),
        context: newWordsContext(
          saved.map((item) => item.term),
          count,
        ),
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      id="learn-get-words"
      title="Get new words"
      description="Your Learn agent picks words you haven't saved yet and adds them to Review."
    >
      <div className="flex flex-col gap-4">
        <div role="group" aria-label="How many words" className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-[var(--ink)]">How many</span>
          <div className="flex gap-2">
            {WORD_COUNTS.map((n) => (
              <button
                key={n}
                type="button"
                aria-pressed={count === n}
                onClick={() => setCount(n)}
                className={`min-h-11 min-w-11 rounded-[var(--radius)] border px-3 text-sm font-medium transition ${
                  count === n
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--canvas)]"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Topic (optional)" htmlFor="learn-topic">
            <Input
              id="learn-topic"
              value={topic}
              maxLength={60}
              placeholder="e.g. travel, cooking"
              className="min-h-11"
              onChange={(e) => setTopic(e.target.value)}
            />
          </Field>
          <Field label="Language" htmlFor="learn-language">
            <Select
              id="learn-language"
              value={language}
              className="min-h-11"
              onChange={(e) => setLanguage(e.target.value)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div>
          <Button className="min-h-11" loading={busy} onClick={() => void getWords()}>
            Get {count} new words
          </Button>
        </div>
      </div>
    </Card>
  );
}

type ReviewState = {
  queue: LearnItem[];
  index: number;
  revealed: boolean;
  busy: boolean;
};

function ReviewArea({ initial, onReviewed }: { initial: LearnItem[]; onReviewed: () => void }) {
  const { toast } = useToast();
  const [state, setState] = useState<ReviewState>(() => ({
    queue: orderReviewQueue(initial),
    index: 0,
    revealed: false,
    busy: false,
  }));
  const [nextDue, setNextDue] = useState<string | null>(null);
  const { queue, index, revealed, busy } = state;
  const current = queue[index];
  const done = index >= queue.length;

  const answer = useCallback(
    async (result: ReviewResult) => {
      const item = queue[index];
      if (!item || busy) return;
      setState((s) => ({ ...s, busy: true }));
      try {
        await reviewLearnItem(item.id, result);
        setState((s) => ({ ...s, index: s.index + 1, revealed: false, busy: false }));
        onReviewed();
      } catch (err) {
        setState((s) => ({ ...s, busy: false }));
        toast(apiErrorMessage(err), "danger");
      }
    },
    [queue, index, busy, onReviewed, toast],
  );

  useEffect(() => {
    if (done) return;
    function onKey(e: KeyboardEvent) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      const tag = el?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el?.isContentEditable) {
        return;
      }
      if (e.key === " " && tag === "BUTTON") return; // let a focused button handle Space
      const action = reviewKeyAction(e.key, state.revealed);
      if (!action) return;
      e.preventDefault();
      if (action === "reveal") setState((s) => ({ ...s, revealed: true }));
      else void answer(action);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [done, state.revealed, answer]);

  useEffect(() => {
    if (!done) return;
    let cancelled = false;
    listLearnItems({})
      .then((all) => {
        if (!cancelled) setNextDue(nextDueIso(all));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [done]);

  if (done) {
    return (
      <Card id="learn-review" title="Review">
        <div className="flex flex-col gap-1 py-4 text-center" aria-live="polite">
          <p className="text-lg font-semibold text-[var(--ink)]">All caught up. Nice work.</p>
          {nextDue ? (
            <p className="text-sm text-[var(--muted)]">
              Next review: {formatDue(nextDue).toLowerCase()}.
            </p>
          ) : null}
        </div>
      </Card>
    );
  }

  return (
    <Card
      id="learn-review"
      title="Review"
      description="Space shows the meaning. Then 1 for Again, 2 for I knew it."
      action={
        <span className="text-sm text-[var(--muted)]" aria-live="polite">
          {queue.length - index} left
        </span>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex min-h-40 flex-col items-center justify-center gap-3 rounded-[var(--radius)] bg-[var(--canvas)] p-6 text-center">
          <p
            className="text-2xl font-semibold text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {current?.term}
          </p>
          {revealed ? (
            <div className="flex flex-col gap-2" aria-live="polite">
              <p className="text-base text-[var(--ink)]">{current?.meaning}</p>
              {current?.example ? (
                <p className="text-sm text-[var(--muted)] italic">{current.example}</p>
              ) : null}
            </div>
          ) : null}
        </div>
        {revealed ? (
          <div className="grid grid-cols-2 gap-3">
            <Button
              variant="secondary"
              className="min-h-11"
              disabled={busy}
              onClick={() => void answer("again")}
            >
              Again
            </Button>
            <Button className="min-h-11" loading={busy} onClick={() => void answer("know")}>
              I knew it
            </Button>
          </div>
        ) : (
          <Button className="min-h-11" onClick={() => setState((s) => ({ ...s, revealed: true }))}>
            Show meaning
          </Button>
        )}
      </div>
    </Card>
  );
}

export function TodayTab() {
  const [stats, setStats] = useState<LearnStats | null>(null);
  const [due, setDue] = useState<LearnItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState(0);

  const load = useCallback(async () => {
    setError(null);
    setDue(null);
    try {
      const [s, d] = await Promise.all([
        getLearnStats(),
        listLearnItems({ due: true, limit: 100 }),
      ]);
      setStats(s);
      setDue(d);
      setSession((n) => n + 1);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
    // New words saved by the Learn agent show up in Review without a page reload.
    const onChanged = () => void load();
    window.addEventListener("compass:data-changed", onChanged);
    return () => window.removeEventListener("compass:data-changed", onChanged);
  }, [load]);

  const refreshStats = useCallback(() => {
    getLearnStats()
      .then(setStats)
      .catch(() => {});
  }, []);

  if (error) return <ErrorBlock what="your learning" message={error} onRetry={() => void load()} />;

  // Words that are due come first: reviewing is the daily habit, asking for new words is secondary.
  const reviewFirst = due !== null && due.length > 0;
  const review =
    due === null || stats === null ? (
      <CardSkeleton />
    ) : stats.total === 0 ? (
      <EmptyState
        title="Nothing saved yet"
        description="Choose how many words below and press Get new words. Your Learn agent saves them here, ready to review."
      />
    ) : due.length === 0 ? (
      <Card id="learn-review" title="Review">
        <p className="py-4 text-center text-sm text-[var(--muted)]" aria-live="polite">
          All caught up. Nice work.
        </p>
      </Card>
    ) : (
      <ReviewArea key={session} initial={due} onReviewed={refreshStats} />
    );

  return (
    <div className="flex flex-col gap-4">
      {stats ? (
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="Due now" value={stats.due} icon={Timer} />
          <KpiCard label="Learned" value={stats.learned} icon={GraduationCap} />
          <KpiCard label="Day streak" value={stats.streak_days} icon={Flame} />
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} heightClass="h-24" className="w-full" />
          ))}
        </div>
      )}
      {reviewFirst ? review : null}
      <GetWordsCard />
      {reviewFirst ? null : review}
    </div>
  );
}
