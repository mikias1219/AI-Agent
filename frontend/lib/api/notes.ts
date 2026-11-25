import { ApiError, api, apiUrl } from "@/lib/api/client";
import { invalidatePrefix } from "@/lib/client-cache/cache";

export type NoteKind = "note" | "diary";
export type Mood = "great" | "good" | "okay" | "low" | "bad";

export type Note = {
  id: string;
  kind: NoteKind;
  title: string;
  body: string;
  tags: string[];
  mood: Mood | null;
  entry_date: string | null;
  pinned: boolean;
  created_at: string;
  updated_at: string;
  drive_url?: string | null;
  drive_synced_at?: string | null;
};

export type NoteStats = {
  notes: number;
  diary_entries: number;
  diary_streak_days: number;
  wrote_diary_today: boolean;
};

export type NoteInput = {
  kind: NoteKind;
  title?: string;
  body: string;
  tags?: string[];
  mood?: Mood | null;
  entry_date?: string;
  pinned?: boolean;
};

export type NotePatch = Partial<Omit<NoteInput, "kind">>;

export type NoteListParams = {
  kind: NoteKind;
  q?: string;
  tag?: string;
  limit?: number;
  offset?: number;
};

function query(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function listNotes(params: NoteListParams): Promise<Note[]> {
  return api<Note[]>(`/notes${query(params)}`);
}

export function getNoteStats(): Promise<NoteStats> {
  return api<NoteStats>("/notes/stats");
}

export function createNote(input: NoteInput): Promise<Note> {
  return api<Note>("/notes", { method: "POST", body: JSON.stringify(input) });
}

export function updateNote(id: string, patch: NotePatch): Promise<Note> {
  return api<Note>(`/notes/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
}

/** DELETE returns 204 with no body, which the JSON client cannot parse. */
export async function deleteNote(id: string): Promise<void> {
  const response = await fetch(apiUrl(`/notes/${id}`), {
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
