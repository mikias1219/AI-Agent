import { api } from "./client";

export type UndoItem = {
  id: string;
  tool_name: string;
  summary: string;
  entity_id: string;
  status: string;
  created_at: string | null;
  expires_at: string | null;
};

export function listUndo() {
  return api<{ items: UndoItem[] }>("/undo");
}

export function applyUndo(id: string) {
  return api<{ id: string; summary: string; undone: boolean }>(`/undo/${encodeURIComponent(id)}`, {
    method: "POST",
  });
}
