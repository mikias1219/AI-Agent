import { ApiError, api, apiUrl } from "@/lib/api/client";
import { invalidatePrefix } from "@/lib/client-cache/cache";

export type FileKind = "file" | "image";

export type FileItem = {
  id: string;
  name: string;
  mime: string;
  size: number;
  kind: FileKind;
  description: string;
  tags: string[];
  created_at: string;
  url: string;
  drive_url?: string | null;
  drive_synced_at?: string | null;
};

export type FileStats = { files: number; images: number; bytes: number };

export type FileUpload = {
  name: string;
  mime: string;
  data_base64: string;
  description?: string;
  tags?: string[];
};

export type FilePatch = { name?: string; description?: string; tags?: string[] };

export type FileListParams = {
  kind?: FileKind;
  q?: string;
  tag?: string;
  limit?: number;
  offset?: number;
};

export function listFiles(params: FileListParams = {}): Promise<FileItem[]> {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return api<FileItem[]>(`/files${s ? `?${s}` : ""}`);
}

export function getFileStats(): Promise<FileStats> {
  return api<FileStats>("/files/stats");
}

export function uploadFile(input: FileUpload): Promise<FileItem> {
  return api<FileItem>("/files", { method: "POST", body: JSON.stringify(input) });
}

export function updateFile(id: string, patch: FilePatch): Promise<FileItem> {
  return api<FileItem>(`/files/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
}

/** DELETE returns 204 with no body, which the JSON client cannot parse. */
export async function deleteFile(id: string): Promise<void> {
  const response = await fetch(apiUrl(`/files/${id}`), {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") message = data.detail;
    } catch {
      /* keep default */
    }
    throw new ApiError(message, response.status);
  }
  invalidatePrefix("GET:");
}

/** Absolute URL for a FileItem.url (which is `/api/files/{id}/content`). */
export function fileContentUrl(item: Pick<FileItem, "url">): string {
  const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");
  return `${base}${item.url}`;
}
