import { api } from "./client";

export type SyncMode = "ask" | "auto";

export type DriveInclude = {
  notes: boolean;
  diary: boolean;
  daily: boolean;
  files: boolean;
  learning: boolean;
  reading: boolean;
};

export type DriveSyncStatus = {
  connected: boolean;
  scope_granted: boolean;
  enabled: boolean;
  mode: SyncMode;
  root_url: string | null;
  last_sync_at: string | null;
  last_error: string | null;
  include: DriveInclude;
  pending: {
    notes: number;
    diary: number;
    daily: number;
    files: number;
    learning: boolean;
    reading: boolean;
  };
};

export type CalendarSyncStatus = {
  connected: boolean;
  scope_granted: boolean;
  enabled: boolean;
  mode: SyncMode;
  last_sync_at: string | null;
  last_error: string | null;
  pending: number;
};

export type SyncRunResult = {
  status: "awaiting_approval" | "done" | "nothing_to_do";
  approval_id: string | null;
  summary: { created: number; updated: number; skipped: number; failed: number } | null;
};

export type DriveItem = {
  object_type: string;
  object_id: string;
  drive_file_id: string;
  drive_url: string;
  synced_at: string;
};

export const driveSync = {
  status: () => api<DriveSyncStatus>("/drive-sync/status", { bypassCache: true }),
  settings: (patch: { enabled?: boolean; include?: Partial<DriveInclude> }) =>
    api<DriveSyncStatus>("/drive-sync/settings", { method: "PATCH", body: JSON.stringify(patch) }),
  run: () => api<SyncRunResult>("/drive-sync/run", { method: "POST", body: "{}" }),
  items: (params: { object_type?: string; limit?: number; offset?: number } = {}) => {
    const sp = new URLSearchParams();
    if (params.object_type) sp.set("object_type", params.object_type);
    sp.set("limit", String(Math.min(200, params.limit ?? 200)));
    if (params.offset) sp.set("offset", String(params.offset));
    return api<DriveItem[]>(`/drive-sync/items?${sp.toString()}`);
  },
};

export const calendarSync = {
  status: () => api<CalendarSyncStatus>("/calendar-sync/status", { bypassCache: true }),
  settings: (patch: { enabled?: boolean }) =>
    api<CalendarSyncStatus>("/calendar-sync/settings", {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  run: () => api<SyncRunResult>("/calendar-sync/run", { method: "POST", body: "{}" }),
};
