"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusChip } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import type { MoneyRow } from "@/lib/api/finance";
import type { HabitToday } from "@/lib/api/habits";
import { patchTask } from "@/lib/api/tasks";
import type {
  DayScore,
  TodayEvent,
  TodayLife,
  TodayNeedsYouItem,
  TodayPlanTask,
} from "@/lib/api/today";
import { formatAmount, formatMoney } from "@/lib/money";
import { HabitChips } from "@/features/habits/habit-chips";
import { reviewMinutes } from "./today-logic";
import { dueLabel } from "@/features/money/occurrence-list";

const LINK =
  "inline-flex min-h-11 items-center text-xs font-medium text-[var(--accent)] hover:underline";

/** The shape every dashboard card shares: one headline number, one line of context, then detail. */
function Headline({ value, sub }: { value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="mb-3 min-w-0">
      <p className="truncate text-2xl leading-tight font-semibold tracking-tight text-[var(--ink)] tabular-nums">
        {value}
      </p>
      {sub ? <p className="mt-0.5 truncate text-xs text-[var(--muted)]">{sub}</p> : null}
    </div>
  );
}

function CardLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className={LINK}>
      {children}
    </Link>
  );
}

function timeOf(startsAt: string): string {
  if (!startsAt) return "";
  const date = new Date(startsAt);
  if (Number.isNaN(date.getTime())) return startsAt;
  if (!startsAt.includes("T")) return "All day";
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

type PlanItem = { id: string; title: string; meta: string; kind: "event" | "task"; high?: boolean };

export function PlanCard({
  events,
  tasks,
  overdue,
  today,
  calendarNote,
  onMoved,
}: {
  events: TodayEvent[];
  tasks: TodayPlanTask[];
  overdue: TodayPlanTask[];
  today: string;
  /** Shown once, only when the calendar is not connected or failed. */
  calendarNote: { message: string; label: string; href: string } | null;
  onMoved: () => void;
}) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(false);
  const items: PlanItem[] = [
    ...events.map((e) => ({
      id: `e-${e.id || e.title}`,
      title: e.title,
      meta: timeOf(e.startsAt),
      kind: "event" as const,
    })),
    ...tasks.map((t) => ({
      id: `t-${t.id}`,
      title: t.title,
      meta: t.due_at ? timeOf(t.due_at) : (t.project ?? ""),
      kind: "task" as const,
      high: t.priority === "p1" || t.priority === "high",
    })),
  ];
  const next = items[0];

  async function moveAll() {
    setBusy(true);
    try {
      await Promise.all(overdue.map((t) => patchTask(t.id, { plan_date: today })));
      toast(`Moved ${overdue.length} to today`, "success");
      onMoved();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      id="today-plan"
      title="Today's plan"
      className="h-full md:col-span-2"
      action={<CardLink href="/tasks">Open Plan</CardLink>}
    >
      <Headline
        value={items.length === 0 ? "A clear day" : `${items.length} on your plate`}
        sub={next ? `Next: ${next.title}${next.meta ? ` · ${next.meta}` : ""}` : undefined}
      />
      {items.length > 0 ? (
        <ul className="mb-3 flex flex-col gap-1.5">
          {items.slice(0, 3).map((item) => (
            <li key={item.id} className="flex min-h-9 items-center gap-3 text-sm">
              <span className="w-16 shrink-0 text-xs text-[var(--muted)] tabular-nums">
                {item.meta || "Today"}
              </span>
              <span className="min-w-0 flex-1 truncate text-[var(--ink)]">{item.title}</span>
              {item.kind === "event" ? <StatusChip tone="accent">Event</StatusChip> : null}
              {item.high ? <StatusChip tone="danger">P1</StatusChip> : null}
            </li>
          ))}
          {items.length > 3 ? (
            <li className="text-xs text-[var(--muted)]">+{items.length - 3} more</li>
          ) : null}
        </ul>
      ) : null}
      {overdue.length > 0 && today ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--warning)_35%,var(--border))] bg-[color-mix(in_srgb,var(--warning)_8%,var(--surface))] px-3 py-2">
          <p className="text-sm font-medium text-[var(--ink)]">{overdue.length} overdue</p>
          <Button size="sm" variant="secondary" loading={busy} onClick={() => void moveAll()}>
            Move to today
          </Button>
        </div>
      ) : null}
      {calendarNote ? (
        <p className="mt-2 text-xs text-[var(--muted)]">
          {calendarNote.message}{" "}
          <Link href={calendarNote.href} className="text-[var(--accent)] hover:underline">
            {calendarNote.label}
          </Link>
        </p>
      ) : null}
    </Card>
  );
}

export function HabitsCard({ data, onChange }: { data: HabitToday; onChange: () => void }) {
  const pct = data.due ? Math.round((data.done / data.due) * 100) : 0;
  return (
    <Card
      id="today-habits"
      title="Habits"
      className="h-full"
      action={<CardLink href="/habits">Manage</CardLink>}
    >
      <Headline value={`${data.done} of ${data.due}`} sub="done today" />
      <div
        className="mb-3 h-1.5 overflow-hidden rounded-full bg-[var(--subtle)]"
        role="progressbar"
        aria-label="Habits done today"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${pct}%` }} />
      </div>
      <HabitChips data={data} onChange={onChange} />
    </Card>
  );
}

export function MoneyCard({ data }: { data: MoneyRow }) {
  return (
    <Card
      id="today-money"
      title="Money"
      className="h-full"
      action={<CardLink href="/money">Add expense</CardLink>}
    >
      <Headline
        value={
          data.left_this_month_minor === null
            ? "No budget yet"
            : `${formatAmount(data.left_this_month_minor)} left`
        }
        sub={data.left_this_month_minor === null ? "Set one in Money" : "this month, ETB"}
      />
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div className="min-w-0">
          <dt className="text-xs text-[var(--muted)]">Spent today</dt>
          <dd className="truncate font-medium text-[var(--ink)] tabular-nums">
            {formatMoney(data.spent_today_minor, data.currency)}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs text-[var(--muted)]">Next bill</dt>
          <dd className="truncate font-medium text-[var(--ink)]">
            {data.next_bill
              ? `${data.next_bill.title} ${dueLabel(data.next_bill.due_date)}`
              : "None soon"}
          </dd>
        </div>
      </dl>
    </Card>
  );
}

export function NeedsYouCard({ items }: { items: TodayNeedsYouItem[] }) {
  return (
    <Card
      id="today-needs-you"
      title="Needs you"
      className="h-full"
      action={<CardLink href="/inbox">Open</CardLink>}
    >
      <Headline
        value={items.length === 0 ? "All clear" : `${items.length} waiting`}
        sub={items.length === 0 ? "Nothing needs a decision" : "approvals and suggestions"}
      />
      <ul className="flex flex-col gap-1.5">
        {items.slice(0, 2).map((item) => (
          <li key={`${item.kind}-${item.id}`} className="flex items-center gap-2 text-sm">
            <span className="min-w-0 flex-1 truncate text-[var(--ink)]">
              {item.summary || item.tool_name || "Approval needed"}
            </span>
            <StatusChip tone={item.risk === "high" ? "danger" : "warning"}>
              {item.kind === "approval" ? "Approval" : "Suggestion"}
            </StatusChip>
          </li>
        ))}
        {items.length > 2 ? (
          <li className="text-xs text-[var(--muted)]">+{items.length - 2} more</li>
        ) : null}
      </ul>
    </Card>
  );
}

/** Day score ring (0-100). The ring is static: motion on data pages must confirm an action only. */
export function ScoreCard({ score }: { score: DayScore }) {
  const total = score.total;
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const dash = total === null ? 0 : (total / 100) * circumference;
  return (
    <Card id="today-score" title="Day score" className="h-full">
      <div className="flex items-center gap-4">
        <svg
          viewBox="0 0 80 80"
          width="80"
          height="80"
          role="img"
          aria-label={`Day score ${total ?? "not available"}`}
        >
          <circle cx="40" cy="40" r={radius} fill="none" stroke="var(--border)" strokeWidth="7" />
          <circle
            cx="40"
            cy="40"
            r={radius}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
            transform="rotate(-90 40 40)"
          />
          <text
            x="40"
            y="46"
            textAnchor="middle"
            className="fill-[var(--ink)] text-xl font-semibold"
          >
            {total ?? "–"}
          </text>
        </svg>
        <div className="min-w-0">
          <p className="text-sm font-medium text-[var(--ink)]">{score.label}</p>
          <p className="text-xs text-[var(--muted)]">Points per area, weights add to 100</p>
        </div>
      </div>
      <ul className="mt-3 flex flex-col gap-1.5">
        {score.areas.map((area) => (
          <li key={area.area} className="flex items-center justify-between gap-3 text-xs">
            <span className="truncate text-[var(--muted)] capitalize">
              {area.area} · {area.detail}
            </span>
            <span className="shrink-0 text-[var(--ink)] tabular-nums">
              {area.points === null ? "–" : `${area.points}/${area.weight}`}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function LearnCard({ learn }: { learn: NonNullable<TodayLife["learn"]> }) {
  return (
    <Card
      id="today-learn"
      title="Words to review"
      className="h-full"
      action={<CardLink href="/learn">{learn.due > 0 ? "Review" : "Open"}</CardLink>}
    >
      <Headline
        value={
          learn.due > 0 ? `${learn.due} due · ~${reviewMinutes(learn.due)} min` : "All caught up"
        }
        sub={learn.due > 0 ? "Quick review, about 20 seconds a word" : `${learn.total} saved`}
      />
    </Card>
  );
}

export function DailyCard({ life }: { life: TodayLife }) {
  const reading = life.reading;
  const diary = life.diary;
  return (
    <Card id="today-daily" title="Reading and diary" className="h-full">
      <dl className="flex flex-col gap-3 text-sm">
        {reading ? (
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <dt className="text-xs text-[var(--muted)]">Reading</dt>
              <dd className="truncate font-medium text-[var(--ink)]">
                {reading.next ?? "No plan yet"}
              </dd>
            </div>
            <CardLink href="/learn?tab=reading">{reading.read_today ? "Done" : "Read"}</CardLink>
          </div>
        ) : null}
        {diary ? (
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <dt className="text-xs text-[var(--muted)]">Diary</dt>
              <dd className="truncate font-medium text-[var(--ink)]">
                {diary.wrote_today ? "Written" : "Not yet today"}
                {diary.streak_days > 0 ? ` · ${diary.streak_days}-day streak` : ""}
              </dd>
            </div>
            <CardLink href="/library?new=diary">{diary.wrote_today ? "Add" : "Write"}</CardLink>
          </div>
        ) : null}
      </dl>
    </Card>
  );
}

export function GoalsCard({ goals }: { goals: { id: string; title: string; progress: number }[] }) {
  const top = goals[0];
  return (
    <Card
      id="today-goals"
      title="Goals"
      className="h-full"
      action={<CardLink href="/goals">Open</CardLink>}
    >
      <Headline
        value={`${goals.length} active`}
        sub={top ? `${top.title} · ${Math.round(top.progress * 100)}%` : undefined}
      />
      {top ? (
        <div
          className="h-1.5 overflow-hidden rounded-full bg-[var(--subtle)]"
          role="progressbar"
          aria-label={`${top.title} progress`}
          aria-valuenow={Math.round(top.progress * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full bg-[var(--accent)]"
            style={{ width: `${Math.round(top.progress * 100)}%` }}
          />
        </div>
      ) : null}
    </Card>
  );
}
