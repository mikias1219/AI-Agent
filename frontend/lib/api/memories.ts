import { api, apiUrl, ApiError } from "./client";
import type { Memory, MemoryKind, MemoryProposal } from "./types";

export type ListMemoriesParams = {
  kind?: MemoryKind;
  q?: string;
};

export type CreateMemoryInput = {
  kind: MemoryKind;
  content: string;
  source_run_id?: string;
};

export type PatchMemoryInput = {
  kind?: MemoryKind;
  content?: string;
};

export async function listMemories(params: ListMemoriesParams = {}): Promise<Memory[]> {
  const query = new URLSearchParams();
  if (params.kind) query.set("kind", params.kind);
  if (params.q?.trim()) query.set("q", params.q.trim());
  const qs = query.toString();
  return api<Memory[]>(qs ? `/memories?${qs}` : "/memories");
}

export async function listMemoryProposals(): Promise<MemoryProposal[]> {
  return api<MemoryProposal[]>("/memories/proposals");
}

export async function confirmMemoryProposal(id: string): Promise<Memory> {
  return api<Memory>(`/memories/proposals/${encodeURIComponent(id)}/confirm`, {
    method: "POST",
    body: "{}",
  });
}

export async function dismissMemoryProposal(id: string): Promise<void> {
  const response = await fetch(apiUrl(`/memories/proposals/${encodeURIComponent(id)}/dismiss`), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!response.ok && response.status !== 204) {
    throw new ApiError("Could not dismiss proposal.", response.status);
  }
}

export async function createMemory(input: CreateMemoryInput): Promise<Memory> {
  return api<Memory>("/memories", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function patchMemory(id: string, input: PatchMemoryInput): Promise<Memory> {
  return api<Memory>(`/memories/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function deleteMemory(id: string): Promise<void> {
  const response = await fetch(apiUrl(`/memories/${id}`), {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok && response.status !== 204) {
    throw new ApiError("Could not delete memory.", response.status);
  }
}

export async function issueForgetToken(): Promise<{
  token: string;
  confirm_phrase: string;
  expires_in_seconds: string;
}> {
  return api("/memories/forget-all/token", { method: "POST", body: "{}" });
}

export async function forgetAllMemories(input: {
  token: string;
  confirm_phrase: string;
}): Promise<{ deleted: number }> {
  return api("/memories/forget-all", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
