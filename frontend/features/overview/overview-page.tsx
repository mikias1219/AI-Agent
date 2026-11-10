"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { MessageSquare } from "lucide-react";
import { buttonClassName } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api/client";
import { getStatus } from "@/lib/api/status";
import type { StatusPayload } from "@/lib/api/types";
import { capabilities } from "@/lib/capabilities";
import { displayName } from "@/lib/auth/session";
import { useAuth } from "@/features/auth/use-auth";
import { HealthStrip } from "./health-strip";
import { SummaryStats, type SummaryStatTile } from "./summary-stats";

const OPEN_STATUSES = new Set(["planned", "in_progress", "blocked"]);

type TaskRow = { id: string; status: string };
type ApprovalRow = { id: string; actionable?: boolean };

type CountsState = {
  openTasks: number | null;
  pendingApprovals: number | null;
  tasksUnavailable: boolean;
  approvalsUnavailable: boolean;
};

export function OverviewPage() {
  const { status: authStatus, loading: authLoading } = useAuth();
  const name = displayName(authStatus?.user);

  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [statusUnavailable, setStatusUnavailable] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);

  const [counts, setCounts] = useState<CountsState>({
    openTasks: null,
    pendingApprovals: null,
    tasksUnavailable: false,
    approvalsUnavailable: false,
  });
  const [countsLoading, setCountsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setStatusLoading(true);
    getStatus()
      .then((payload) => {
        if (cancelled) return;
        setStatus(payload);
        setStatusUnavailable(false);
      })
      .catch(() => {
        if (cancelled) return;
        setStatus(null);
        setStatusUnavailable(true);
      })
      .finally(() => {
        if (!cancelled) setStatusLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setCountsLoading(true);

    Promise.all([
      api<TaskRow[]>("/tasks").catch(() => null),
      api<ApprovalRow[]>("/approvals").catch(() => null),
    ]).then(([tasks, approvals]) => {
      if (cancelled) return;
      if (tasks === null) {
        setCounts((prev) => ({
          ...prev,
          openTasks: null,
          tasksUnavailable: true,
        }));
      } else {
        const open = tasks.filter((t) => OPEN_STATUSES.has(t.status)).length;
        setCounts((prev) => ({
          ...prev,
          openTasks: open,
          tasksUnavailable: false,
        }));
      }
      if (approvals === null) {
        setCounts((prev) => ({
          ...prev,
          pendingApprovals: null,
          approvalsUnavailable: true,
        }));
      } else {
        const pending = approvals.filter((a) => a.actionable).length;
        setCounts((prev) => ({
          ...prev,
          pendingApprovals: pending,
          approvalsUnavailable: false,
        }));
      }
      setCountsLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const tiles = useMemo((): SummaryStatTile[] => {
    const telegram = status?.telegram;
    let telegramValue: string;
    let telegramDetail: string;
    if (statusUnavailable) {
      telegramValue = "—";
      telegramDetail = "Status unavailable";
    } else if (!telegram?.configured) {
      telegramValue = "Off";
      telegramDetail = "Connect on the Telegram page";
    } else if (telegram.managed) {
      telegramValue = "On";
      telegramDetail =
        telegram.runtime === "running" ? "Bot managed and running" : "Bot configured and managed";
    } else {
      telegramValue = "Setup";
      telegramDetail = "Configured — finish setup in Connections";
    }

    const socialPreview = capabilities.linkedin === "mock" && capabilities.facebook === "mock";

    return [
      {
        label: "Open tasks",
        value: countsLoading ? "…" : counts.tasksUnavailable ? "—" : (counts.openTasks ?? 0),
        detail: counts.tasksUnavailable
          ? "Tasks API offline"
          : counts.openTasks === 0
            ? "Nothing in progress"
            : "View and update on Tasks",
        href: "/tasks",
      },
      {
        label: "Pending approvals",
        value: countsLoading
          ? "…"
          : counts.approvalsUnavailable
            ? "—"
            : (counts.pendingApprovals ?? 0),
        detail: counts.approvalsUnavailable
          ? "Approvals API offline"
          : counts.pendingApprovals === 0
            ? "Nothing waiting for review"
            : "Review on Tasks",
        href: "/tasks",
      },
      {
        label: "Telegram",
        value: statusLoading ? "…" : telegramValue,
        detail: telegramDetail,
        href: "/connections/telegram",
      },
      {
        label: "Google & social",
        value: socialPreview ? "Preview" : "Live",
        detail: socialPreview ? "Sample data only — integrations pending" : "Connected channels",
        href: "/connections",
      },
    ];
  }, [counts, countsLoading, status, statusLoading, statusUnavailable]);

  const loading = authLoading && !authStatus;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-5 py-6 sm:px-7 sm:py-8">
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Overview</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)] sm:text-3xl"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {loading ? "Good day" : `Good day, ${name}`}
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--muted)]">
          A quick read on your work and connections — open a page below for the full view.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Link href="/chat" className={buttonClassName("primary", "md", "gap-2 no-underline")}>
            <MessageSquare className="size-4" aria-hidden />
            Ask agent
          </Link>
          <Link href="/tasks" className="text-sm font-medium text-[var(--accent)] hover:underline">
            Go to tasks
          </Link>
        </div>
      </header>

      {(statusLoading || countsLoading) && !status && counts.openTasks === null ? (
        <div className="flex items-center justify-center gap-2 py-6 text-sm text-[var(--muted)]">
          <Spinner size="sm" />
          Loading summary…
        </div>
      ) : null}

      <SummaryStats tiles={tiles} />
      <HealthStrip status={status} statusUnavailable={statusUnavailable} />
    </div>
  );
}
