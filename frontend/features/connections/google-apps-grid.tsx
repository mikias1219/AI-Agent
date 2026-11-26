"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CalendarDays,
  FileSpreadsheet,
  FileText,
  FolderOpen,
  Mail,
  ShieldCheck,
} from "lucide-react";
import type { ComponentType } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { getGoogleStatus, type GoogleStatus } from "@/lib/api/google";

type AppRow = {
  key: "gmail" | "calendar" | "drive" | "docs" | "sheets";
  /** Scope fragment that proves the app is granted (docs and sheets have no service flag). */
  scope?: string;
  name: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  href: string;
  reads: string;
  changes: string;
};

const APPS: AppRow[] = [
  {
    key: "gmail",
    name: "Gmail",
    icon: Mail,
    href: "/mail",
    reads: "Search, read and summarise mail",
    changes: "Draft, reply and send, each asks you first",
  },
  {
    key: "calendar",
    name: "Calendar",
    icon: CalendarDays,
    href: "/calendar",
    reads: "List events and find free time",
    changes: "Create, update and delete events, each asks you first",
  },
  {
    key: "drive",
    name: "Drive",
    icon: FolderOpen,
    href: "/connections/google",
    reads: "Search files and read their text",
    changes: "No changes",
  },
  {
    key: "docs",
    name: "Docs",
    icon: FileText,
    href: "/connections/google",
    scope: "documents",
    reads: "Read documents through Drive",
    changes: "Create documents and add text, each asks you first",
  },
  {
    key: "sheets",
    name: "Sheets",
    icon: FileSpreadsheet,
    href: "/connections/google",
    scope: "spreadsheets",
    reads: "Read ranges",
    changes: "Append rows, each asks you first",
  },
];

/** One card per Google app: what Compass can do there and whether it is on. Reads only the live status. */
export function GoogleAppsGrid() {
  const [status, setStatus] = useState<GoogleStatus | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    getGoogleStatus()
      .then((next) => !cancelled && setStatus(next))
      .catch(() => !cancelled && setStatus(null));
    return () => {
      cancelled = true;
    };
  }, []);

  const connected = Boolean(status?.connected);
  // Until Google is connected the Google card above already says what to do; a list of "Not connected" rows is noise.
  if (status === undefined || status === null || !connected) return null;
  const readOnly = status?.read_only !== false;

  return (
    <Card
      id="google-apps"
      title="Google apps"
      description={
        connected
          ? `${status?.email ? `Connected as ${status.email}. ` : ""}${readOnly ? "Read-only mode: Compass cannot change anything." : "Changes always ask you first."}`
          : "Connect Google once to use all of these."
      }
      action={
        <Link
          href="/connections/google"
          className="text-xs font-medium text-[var(--accent)] hover:underline"
        >
          Manage
        </Link>
      }
      flush
    >
      <ul className="divide-y divide-[var(--border)] border-t border-[var(--border)]">
        {APPS.map((app) => {
          const Icon = app.icon;
          const on =
            connected &&
            (app.scope
              ? Boolean(status?.scopes?.includes(app.scope))
              : app.key === "gmail" || app.key === "calendar" || app.key === "drive"
                ? status?.services?.[app.key]
                : false);
          return (
            <li key={app.key} className="flex flex-wrap items-center gap-4 px-4 py-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <Link
                  href={app.href}
                  className="text-sm font-medium text-[var(--ink)] hover:underline"
                >
                  {app.name}
                </Link>
                <p className="text-[length:var(--text-caption)] text-[var(--muted)]">
                  {app.reads}.{" "}
                  {readOnly && connected ? "Changes are switched off." : app.changes + "."}
                </p>
              </div>
              {status === undefined ? (
                <Badge tone="neutral">Checking</Badge>
              ) : status === null ? (
                <Badge tone="warning">Unavailable</Badge>
              ) : on ? (
                <Badge tone="success">On</Badge>
              ) : (
                <Badge tone="neutral">Not connected</Badge>
              )}
            </li>
          );
        })}
      </ul>
      {connected && status?.scope_labels?.length ? (
        <div className="flex items-start gap-2 border-t border-[var(--border)] px-4 py-3 text-[length:var(--text-caption)] text-[var(--muted)]">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <span>Permissions granted: {status.scope_labels.map((s) => s.label).join(", ")}.</span>
        </div>
      ) : null}
    </Card>
  );
}
