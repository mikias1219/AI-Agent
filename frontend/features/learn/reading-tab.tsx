"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, ChevronDown, ChevronRight, Flame, MoreHorizontal, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { KpiCard } from "@/components/ui/kpi-card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusChip } from "@/components/ui/status-chip";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  advanceReadingPlan,
  createReadingPlan,
  deleteReadingPlan,
  getReadingStats,
  listReadingLogs,
  listReadingPlans,
  listReadingTemplates,
  updateReadingPlan,
  type ReadingLog,
  type ReadingPlan,
  type ReadingStats,
  type ReadingTemplate,
} from "@/lib/api/reading";
import { ConfirmModal } from "./confirm-modal";
import {
  explainPassageHref,
  parseReferenceList,
  previewText,
  progressPercent,
} from "./learn-logic";
import { LogDrawer, type LogDrawerState } from "./log-drawer";
import { CardSkeleton, ErrorBlock } from "./states";

const CUSTOM = "custom";

function PlanSetup({ paused, onChanged }: { paused: ReadingPlan[]; onChanged: () => void }) {
  const { toast } = useToast();
  const [templates, setTemplates] = useState<ReadingTemplate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [choice, setChoice] = useState<string>("");
  const [custom, setCustom] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadTemplates = useCallback(async () => {
    setError(null);
    try {
      const t = await listReadingTemplates();
      setTemplates(t);
      setChoice((c) => c || t[0]?.id || CUSTOM);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  async function start() {
    setFormError(null);
    setBusy(true);
    try {
      if (choice === CUSTOM) {
        const items = parseReferenceList(custom);
        if (items.length === 0) {
          setFormError("Add at least one passage, one per line.");
          return;
        }
        await createReadingPlan({ name: name.trim() || "My reading list", items });
      } else {
        const tpl = templates?.find((t) => t.id === choice);
        await createReadingPlan({ name: tpl?.name ?? "Reading plan", template: choice });
      }
      toast("Plan started.", "success");
      onChanged();
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function resume(plan: ReadingPlan) {
    try {
      await updateReadingPlan(plan.id, { active: true });
      onChanged();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  if (error)
    return <ErrorBlock what="reading plans" message={error} onRetry={() => void loadTemplates()} />;
  if (!templates) return <CardSkeleton rows={4} />;

  const options = [
    ...templates.map((t) => ({
      id: t.id,
      title: t.name,
      sub: `${t.description} (${t.count} ${t.count === 1 ? "passage" : "passages"})`,
    })),
    { id: CUSTOM, title: "Use my own list", sub: "Type the passages you want to read." },
  ];

  return (
    <div className="flex flex-col gap-4">
      <Card
        id="reading-start"
        title="Start a reading plan"
        description="One passage at a time. Pick a plan and Compass keeps track of where you are."
      >
        <div className="flex flex-col gap-4">
          <div role="radiogroup" aria-label="Reading plan" className="flex flex-col gap-2">
            {options.map((o) => {
              const selected = choice === o.id;
              return (
                <label
                  key={o.id}
                  className={`flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--radius)] border p-3 transition focus-within:outline-2 focus-within:outline-[var(--accent)] ${
                    selected
                      ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                      : "border-[var(--border)] hover:bg-[var(--canvas)]"
                  }`}
                >
                  <input
                    type="radio"
                    name="reading-plan"
                    className="mt-1 accent-[var(--accent)]"
                    checked={selected}
                    onChange={() => setChoice(o.id)}
                  />
                  <span className="flex flex-col">
                    <span className="text-sm font-medium text-[var(--ink)]">{o.title}</span>
                    <span className="text-[length:var(--text-caption)] text-[var(--muted)]">
                      {o.sub}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
          {choice === CUSTOM ? (
            <div className="flex flex-col gap-4">
              <Field label="Plan name" htmlFor="plan-name">
                <Input
                  id="plan-name"
                  value={name}
                  maxLength={120}
                  placeholder="My reading list"
                  className="min-h-11"
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Passages, one per line" htmlFor="plan-custom">
                <Textarea
                  id="plan-custom"
                  rows={6}
                  value={custom}
                  placeholder={"John 1\nJohn 2\nJohn 3:1-21"}
                  onChange={(e) => setCustom(e.target.value)}
                />
              </Field>
            </div>
          ) : null}
          {formError ? (
            <p role="alert" className="text-sm text-[var(--danger)]">
              {formError}
            </p>
          ) : null}
          <div>
            <Button className="min-h-11" loading={busy} onClick={() => void start()}>
              Start plan
            </Button>
          </div>
        </div>
      </Card>
      {paused.length > 0 ? (
        <Card id="reading-paused" title="Paused plans">
          <ul className="flex flex-col gap-2">
            {paused.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm text-[var(--ink)]">
                  {p.name}{" "}
                  <span className="text-[var(--muted)]">({progressPercent(p.progress)}% done)</span>
                </span>
                <Button variant="secondary" className="min-h-11" onClick={() => void resume(p)}>
                  Resume
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}

function PlanHero({ plan, onChanged }: { plan: ReadingPlan; onChanged: () => void }) {
  const { toast } = useToast();
  const [showReflection, setShowReflection] = useState(false);
  const [reflection, setReflection] = useState("");
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const pct = progressPercent(plan.progress);
  const finished = plan.next === null;

  async function markRead() {
    setBusy(true);
    try {
      await advanceReadingPlan(plan.id, reflection.trim() || undefined);
      setReflection("");
      setShowReflection(false);
      toast("Marked as read.", "success");
      onChanged();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  async function pause() {
    setMenu(false);
    try {
      await updateReadingPlan(plan.id, { active: false });
      onChanged();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await deleteReadingPlan(plan.id);
      setConfirmDelete(false);
      toast("Plan deleted.", "success");
      onChanged();
    } catch (err) {
      setConfirmDelete(false);
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      id="reading-hero"
      title={plan.name}
      action={
        <div className="relative">
          <Button
            variant="secondary"
            className="min-h-11 min-w-11"
            aria-label="Plan options"
            aria-expanded={menu}
            onClick={() => setMenu((m) => !m)}
          >
            <MoreHorizontal className="h-4 w-4" aria-hidden />
          </Button>
          {menu ? (
            <div
              role="group"
              aria-label="Plan options"
              className="absolute right-0 z-10 mt-1 flex w-52 flex-col rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-1 shadow-lg"
              onKeyDown={(e) => {
                if (e.key === "Escape") setMenu(false);
              }}
            >
              <button
                type="button"
                className="min-h-11 rounded-md px-3 text-left text-sm hover:bg-[var(--canvas)]"
                onClick={() => void pause()}
              >
                Pause or switch plan
              </button>
              <button
                type="button"
                className="min-h-11 rounded-md px-3 text-left text-sm text-[var(--danger)] hover:bg-[var(--canvas)]"
                onClick={() => {
                  setMenu(false);
                  setConfirmDelete(true);
                }}
              >
                Delete plan
              </button>
            </div>
          ) : null}
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <div
            role="progressbar"
            aria-label="Plan progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={pct}
            className="h-2 overflow-hidden rounded-full bg-[var(--border)]"
          >
            <div className="h-full bg-[var(--accent)]" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-[length:var(--text-caption)] text-[var(--muted)]">
            {pct}% complete ({plan.position} of {plan.items.length})
          </p>
        </div>
        {finished ? (
          <div className="flex flex-col gap-1 py-2" aria-live="polite">
            <p className="text-xl font-semibold text-[var(--ink)]">Plan finished. Well done.</p>
            <p className="text-sm text-[var(--muted)]">
              Start another plan from the options menu whenever you are ready.
            </p>
          </div>
        ) : (
          <>
            <p
              className="text-2xl font-semibold text-[var(--ink)] sm:text-3xl"
              style={{ fontFamily: "var(--font-display)" }}
            >
              Next: {plan.next}
            </p>
            <div className="flex flex-col gap-2">
              <button
                type="button"
                aria-expanded={showReflection}
                aria-controls="reading-reflection"
                onClick={() => setShowReflection((s) => !s)}
                className="inline-flex min-h-11 w-fit items-center gap-1 text-sm font-medium text-[var(--accent)]"
              >
                {showReflection ? (
                  <ChevronDown className="h-4 w-4" aria-hidden />
                ) : (
                  <ChevronRight className="h-4 w-4" aria-hidden />
                )}
                Reflection (optional)
              </button>
              {showReflection ? (
                <Textarea
                  id="reading-reflection"
                  aria-label="Reflection"
                  rows={4}
                  maxLength={5000}
                  placeholder="What stood out to you?"
                  value={reflection}
                  onChange={(e) => setReflection(e.target.value)}
                />
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <Button className="min-h-11" loading={busy} onClick={() => void markRead()}>
                Mark as read
              </Button>
              <Link
                href={explainPassageHref(plan.next ?? "")}
                className="text-sm text-[var(--accent)] underline-offset-2 hover:underline"
              >
                Ask Compass to explain this passage
              </Link>
            </div>
          </>
        )}
      </div>
      <ConfirmModal
        open={confirmDelete}
        title="Delete this plan?"
        message="The plan is removed. Your reading log stays."
        confirmLabel="Delete plan"
        busy={busy}
        onConfirm={() => void remove()}
        onClose={() => setConfirmDelete(false)}
      />
    </Card>
  );
}

const logColumns: Column<ReadingLog>[] = [
  {
    id: "date",
    header: "Date",
    cell: (r) => <span className="whitespace-nowrap">{r.read_on}</span>,
    sortValue: (r) => r.read_on,
    width: "w-32",
  },
  {
    id: "reference",
    header: "Passage",
    cell: (r) => <span className="font-medium text-[var(--ink)]">{r.reference}</span>,
    sortValue: (r) => r.reference.toLowerCase(),
  },
  {
    id: "reflection",
    header: "Reflection",
    cell: (r) => (
      <span className="text-[var(--muted)]">{previewText(r.reflection, 100) || "None"}</span>
    ),
    hideOnMobile: true,
  },
];

export function ReadingTab() {
  const [stats, setStats] = useState<ReadingStats | null>(null);
  const [paused, setPaused] = useState<ReadingPlan[]>([]);
  const [logs, setLogs] = useState<ReadingLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [logsLoading, setLogsLoading] = useState(true);
  const [drawer, setDrawer] = useState<LogDrawerState>(null);

  const load = useCallback(async () => {
    setError(null);
    setLogsLoading(true);
    try {
      const [s, plans, l] = await Promise.all([
        getReadingStats(),
        listReadingPlans().catch(() => [] as ReadingPlan[]),
        listReadingLogs(),
      ]);
      setStats(s);
      setPaused(plans.filter((p) => !p.active));
      setLogs(l);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLogsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <ErrorBlock what="your reading" message={error} onRetry={() => void load()} />;
  if (!stats) {
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        <CardSkeleton rows={4} />
        <div className="grid grid-cols-2 gap-3">
          <Skeleton heightClass="h-24" className="w-full" />
          <Skeleton heightClass="h-24" className="w-full" />
        </div>
      </div>
    );
  }

  const plan = stats.active_plan;
  return (
    <div className="flex flex-col gap-4">
      {plan ? (
        <PlanHero key={plan.id} plan={plan} onChanged={() => void load()} />
      ) : (
        <PlanSetup paused={paused} onChanged={() => void load()} />
      )}
      <div className="grid grid-cols-2 gap-3">
        <KpiCard label="Day streak" value={stats.streak_days} icon={Flame} />
        <KpiCard label="Passages read" value={stats.logs} icon={BookOpen} hint={undefined} />
      </div>
      <div>
        <StatusChip tone={stats.read_today ? "success" : "neutral"}>
          {stats.read_today ? "Read today" : "Not read yet today"}
        </StatusChip>
      </div>
      <Card
        id="reading-log"
        title="Reading log"
        flush
        action={
          <Button
            variant="secondary"
            className="min-h-11"
            onClick={() => setDrawer({ mode: "add" })}
          >
            <Plus className="h-4 w-4" aria-hidden />
            Log a reading
          </Button>
        }
      >
        <DataTable
          label="Reading log"
          columns={logColumns}
          rows={logs}
          rowKey={(r) => r.id}
          loading={logsLoading}
          empty={{
            title: "No readings yet",
            description: plan
              ? "Mark today's passage as read and it shows up here."
              : "Start a plan above, or use Log a reading for any passage.",
          }}
          onRowClick={(r) => setDrawer({ mode: "edit", log: r })}
          selectedKey={drawer?.mode === "edit" ? drawer.log.id : null}
          initialSort={{ id: "date", dir: "desc" }}
        />
      </Card>
      <LogDrawer state={drawer} onClose={() => setDrawer(null)} onSaved={() => void load()} />
    </div>
  );
}
