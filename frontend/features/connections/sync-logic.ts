import type { CalendarSyncStatus, DriveSyncStatus, SyncMode, SyncRunResult } from "@/lib/api/sync";

export type DriveKey = keyof DriveSyncStatus["include"];

export const DRIVE_INCLUDE_LABEL: Record<DriveKey, string> = {
  notes: "Notes",
  diary: "Diary",
  daily: "Daily summaries",
  files: "Files",
  learning: "Learning words",
  reading: "Reading log",
};

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

/** Pending items in words, only for areas that are included. Empty when everything is backed up. */
export function drivePendingWords(status: Pick<DriveSyncStatus, "include" | "pending">): string[] {
  const { include, pending } = status;
  const out: string[] = [];
  if (include.notes && pending.notes > 0) out.push(plural(pending.notes, "note", "notes"));
  if (include.diary && pending.diary > 0)
    out.push(plural(pending.diary, "diary entry", "diary entries"));
  if (include.daily && pending.daily > 0)
    out.push(plural(pending.daily, "daily summary", "daily summaries"));
  if (include.files && pending.files > 0) out.push(plural(pending.files, "file", "files"));
  if (include.learning && pending.learning) out.push("learning words");
  if (include.reading && pending.reading) out.push("reading log");
  return out;
}

export function calendarPendingWords(pending: number): string {
  return pending > 0 ? plural(pending, "task", "tasks") : "";
}

export function modeLine(mode: SyncMode, what: "backup" | "calendar"): string {
  const noun = what === "backup" ? "backup" : "calendar update";
  return mode === "auto"
    ? "Automatic: you allowed this in Permissions."
    : `AURA asks you first for each ${noun}.`;
}

export type SyncChip = { label: string; tone: "success" | "warning" | "neutral" | "danger" };

export function syncChip(
  status: Pick<
    DriveSyncStatus | CalendarSyncStatus,
    "connected" | "scope_granted" | "enabled" | "last_error"
  >,
): SyncChip {
  if (!status.connected) return { label: "Google not connected", tone: "neutral" };
  if (!status.scope_granted) return { label: "Needs reconnect", tone: "warning" };
  if (status.last_error) return { label: "Last run failed", tone: "danger" };
  return status.enabled ? { label: "On", tone: "success" } : { label: "Off", tone: "neutral" };
}

/** Honest message for the result of a run. Never claims a sync unless the API said so. */
export function runMessage(result: SyncRunResult): string {
  if (result.status === "awaiting_approval") return "Waiting for your OK in Needs you";
  if (result.status === "nothing_to_do") return "Nothing to back up right now.";
  const s = result.summary;
  if (!s) return "Finished.";
  const parts = [
    s.created > 0 ? `${s.created} created` : "",
    s.updated > 0 ? `${s.updated} updated` : "",
    s.skipped > 0 ? `${s.skipped} unchanged` : "",
    s.failed > 0 ? `${s.failed} failed` : "",
  ].filter(Boolean);
  return parts.length > 0 ? `Done: ${parts.join(", ")}.` : "Finished.";
}
