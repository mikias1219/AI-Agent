"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SkeletonRows } from "@/components/ui/skeleton";
import { StatusChip } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  calendarSync,
  driveSync,
  type CalendarSyncStatus,
  type DriveSyncStatus,
  type SyncRunResult,
} from "@/lib/api/sync";
import { formatWhen } from "./format";
import {
  DRIVE_INCLUDE_LABEL,
  calendarPendingWords,
  drivePendingWords,
  modeLine,
  runMessage,
  syncChip,
  type DriveKey,
} from "./sync-logic";

const linkClass =
  "inline-flex min-h-11 items-center text-sm font-medium text-[var(--accent)] underline";

type RowProps = {
  title: string;
  status: Pick<
    DriveSyncStatus,
    "connected" | "scope_granted" | "enabled" | "last_error" | "last_sync_at" | "mode"
  >;
  what: "backup" | "calendar";
  intro: string;
  extra?: ReactNode;
  pendingText: string;
  busy: boolean;
  result: SyncRunResult | null;
  onToggle: (enabled: boolean) => void;
  onRun: () => void;
  runLabel: string;
};

function SyncRow({
  title,
  status,
  what,
  intro,
  extra,
  pendingText,
  busy,
  result,
  onToggle,
  onRun,
  runLabel,
}: RowProps) {
  const chip = syncChip(status);
  const ready = status.connected && status.scope_granted;
  return (
    <div className="flex flex-col gap-3 px-1 py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--ink)]">{title}</h3>
        <StatusChip tone={chip.tone}>{chip.label}</StatusChip>
      </div>
      <p className="text-sm text-[var(--muted)]">{intro}</p>

      {!status.connected ? (
        <Link href="/connections/google" className={linkClass}>
          Connect Google
        </Link>
      ) : !status.scope_granted ? (
        <Link href="/connections/google" className={linkClass}>
          Reconnect Google to allow {what === "backup" ? "Drive backup" : "Calendar sync"}
        </Link>
      ) : (
        <>
          <label className="flex min-h-11 items-center gap-3 text-sm text-[var(--ink)]">
            <input
              type="checkbox"
              className="h-5 w-5"
              checked={status.enabled}
              disabled={busy}
              onChange={(event) => onToggle(event.target.checked)}
            />
            {what === "backup" ? "Back up to Google Drive" : "Sync tasks to Google Calendar"}
          </label>
          {extra}
          <p className="text-sm text-[var(--muted)]">{modeLine(status.mode, what)}</p>
          <p className="text-sm text-[var(--muted)]" aria-live="polite">
            {pendingText
              ? `Waiting to go: ${pendingText}.`
              : status.enabled
                ? "Nothing is waiting."
                : "Turn this on to see what is waiting."}{" "}
            {status.last_sync_at ? `Last run: ${formatWhen(status.last_sync_at)}.` : "No run yet."}
          </p>
          {status.last_error ? (
            <p className="text-sm text-[var(--danger)]" role="alert">
              {status.last_error}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-3">
            <Button
              className="min-h-11"
              loading={busy}
              disabled={busy || !status.enabled || !ready}
              onClick={onRun}
            >
              {runLabel}
            </Button>
            {result ? (
              <p className="text-sm text-[var(--ink)]" role="status">
                {runMessage(result)}
                {result.status === "awaiting_approval" ? (
                  <>
                    {" "}
                    <Link href="/inbox" className="font-medium text-[var(--accent)] underline">
                      Open Needs you
                    </Link>
                  </>
                ) : null}
              </p>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}

export function BackupSyncCard() {
  const { toast } = useToast();
  const [drive, setDrive] = useState<DriveSyncStatus | null>(null);
  const [calendar, setCalendar] = useState<CalendarSyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"drive" | "calendar" | null>(null);
  const [driveResult, setDriveResult] = useState<SyncRunResult | null>(null);
  const [calendarResult, setCalendarResult] = useState<SyncRunResult | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [d, c] = await Promise.all([driveSync.status(), calendarSync.status()]);
      setDrive(d);
      setCalendar(c);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(which: "drive" | "calendar") {
    setBusy(which);
    try {
      const result = await (which === "drive" ? driveSync.run() : calendarSync.run());
      (which === "drive" ? setDriveResult : setCalendarResult)(result);
      await load();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(null);
    }
  }

  async function toggleDrive(patch: Parameters<typeof driveSync.settings>[0]) {
    setBusy("drive");
    try {
      setDrive(await driveSync.settings(patch));
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card
      id="backup-sync-title"
      title="Backup and sync"
      description="Keep your notes and tasks safe in your own Google account."
    >
      {loading ? <SkeletonRows count={2} /> : null}
      {!loading && error ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
          <Button variant="secondary" size="sm" onClick={() => void load()}>
            Try again
          </Button>
        </div>
      ) : null}
      {!loading && !error && drive && calendar ? (
        <div className="flex flex-col divide-y divide-[var(--border)]">
          <SyncRow
            title="Google Drive backup"
            what="backup"
            status={drive}
            intro="Copies your notes, diary and daily summaries into an organized AURA folder. Nothing outside that folder is read or changed, and deleting here never deletes in Drive."
            extra={
              <div className="flex flex-col gap-1">
                {drive.root_url ? (
                  <a
                    href={drive.root_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={linkClass}
                  >
                    Open the AURA/ folder
                  </a>
                ) : null}
                <fieldset className="min-w-0">
                  <legend className="text-sm font-medium text-[var(--ink)]">
                    What is included
                  </legend>
                  <div className="grid gap-x-4 sm:grid-cols-2">
                    {(Object.keys(DRIVE_INCLUDE_LABEL) as DriveKey[]).map((key) => (
                      <label
                        key={key}
                        className="flex min-h-11 items-center gap-3 text-sm text-[var(--ink)]"
                      >
                        <input
                          type="checkbox"
                          className="h-5 w-5"
                          checked={drive.include[key]}
                          disabled={busy === "drive"}
                          onChange={(event) =>
                            void toggleDrive({ include: { [key]: event.target.checked } })
                          }
                        />
                        {DRIVE_INCLUDE_LABEL[key]}
                      </label>
                    ))}
                  </div>
                </fieldset>
              </div>
            }
            pendingText={drivePendingWords(drive).join(", ")}
            busy={busy === "drive"}
            result={driveResult}
            onToggle={(enabled) => void toggleDrive({ enabled })}
            onRun={() => void run("drive")}
            runLabel="Back up now"
          />
          <SyncRow
            title="Google Calendar sync"
            what="calendar"
            status={calendar}
            intro="Tasks with a time show up as events in your calendar. When you complete one, its event title gets a check mark."
            pendingText={calendarPendingWords(calendar.pending)}
            busy={busy === "calendar"}
            result={calendarResult}
            onToggle={async (enabled) => {
              setBusy("calendar");
              try {
                setCalendar(await calendarSync.settings({ enabled }));
              } catch (err) {
                toast(apiErrorMessage(err), "danger");
              } finally {
                setBusy(null);
              }
            }}
            onRun={() => void run("calendar")}
            runLabel="Sync tasks now"
          />
        </div>
      ) : null}
    </Card>
  );
}
