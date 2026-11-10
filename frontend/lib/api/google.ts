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

export type GoogleStatus = {
  oauth_configured: boolean;
  connected: boolean;
  has_tokens?: boolean;
  email: string;
  services: { gmail: boolean; calendar: boolean; drive: boolean };
};

export function getGoogleStatus() {
  return api<GoogleStatus>("/google/status");
}

export function connectGoogle() {
  return api<{ auth_url: string; local_dev_connected?: boolean }>("/google/connect", {
    method: "POST",
  });
}

export function disconnectGoogle() {
  return api<{ disconnected: boolean }>("/google/disconnect", { method: "POST" });
}

export function listGmail(page = 1, pageSize = 8) {
  return api<GooglePage<GoogleMessage>>(
    `/google/gmail?page=${page}&page_size=${pageSize}`,
  );
}

export function listCalendar(page = 1, pageSize = 8) {
  return api<GooglePage<GoogleEvent>>(
    `/google/calendar?page=${page}&page_size=${pageSize}`,
  );
}

export function listDrive(page = 1, pageSize = 8) {
  return api<GooglePage<GoogleFile>>(`/google/drive?page=${page}&page_size=${pageSize}`);
}
