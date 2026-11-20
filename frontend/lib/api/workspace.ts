import { api, apiUrl } from "./client";

export type WorkspaceExport = Record<string, unknown>;

export type WipeToken = {
  token: string;
  confirm_phrase: string;
};

export type WipeResult = {
  wiped: boolean;
  deleted: Record<string, number>;
  google_cleared: boolean;
};

export function exportWorkspace(): Promise<WorkspaceExport> {
  return api<WorkspaceExport>("/export");
}

export function exportWorkspaceUrl(): string {
  return apiUrl("/export");
}

export function issueWipeToken(): Promise<WipeToken> {
  return api<WipeToken>("/workspace/wipe/token", { method: "POST" });
}

export function wipeWorkspace(body: {
  token: string;
  confirm_phrase: string;
}): Promise<WipeResult> {
  return api<WipeResult>("/workspace/wipe", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
