import { api } from "./client";

export type GoogleMessage = {
  id: string;
  from: string;
  subject: string;
  snippet: string;
  receivedAt: string;
};

export type GoogleEvent = {
  id: string;
  title: string;
  startsAt: string;
  location: string;
};

export type GoogleFile = {
  id: string;
  name: string;
  kind: string;
  updatedAt: string;
};

export type GooglePage<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export type GoogleScopeLabel = { scope: string; label: string };

export type GoogleStatus = {
  oauth_configured: boolean;
  connected: boolean;
  has_tokens?: boolean;
  email: string;
  read_only?: boolean;
  scopes?: string;
  scope_labels?: GoogleScopeLabel[];
  auth_url?: string;
  services: { gmail: boolean; calendar: boolean; drive: boolean };
};

export function getGoogleStatus() {
  return api<GoogleStatus>("/google/status");
}

export function connectGoogle(readOnly = true) {
  return api<{ auth_url: string; local_dev_connected?: boolean; read_only?: boolean }>(
    `/google/connect?read_only=${readOnly ? "true" : "false"}`,
    { method: "POST" },
  );
}

export function patchGoogleSettings(input: { read_only: boolean }) {
  return api<GoogleStatus>("/google/settings", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function disconnectGoogle() {
  return api<{ disconnected: boolean }>("/google/disconnect", { method: "POST" });
}

export function listGmail(page = 1, pageSize = 8) {
  return api<GooglePage<GoogleMessage>>(`/google/gmail?page=${page}&page_size=${pageSize}`);
}

export function listCalendar(page = 1, pageSize = 8) {
  return api<GooglePage<GoogleEvent>>(`/google/calendar?page=${page}&page_size=${pageSize}`);
}

export function listDrive(page = 1, pageSize = 8) {
  return api<GooglePage<GoogleFile>>(`/google/drive?page=${page}&page_size=${pageSize}`);
}
