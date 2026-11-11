import { ApiError, api, apiUrl } from "./client";
import type { RunEvent, RunSummary } from "./types";

export type StartRunInput = { text: string; sessionId?: string };

export async function startRun(input: StartRunInput): Promise<RunSummary> {
  const payload: { text: string; session_id?: string } = { text: input.text.trim() };
  if (input.sessionId) payload.session_id = input.sessionId;
  return api<RunSummary>("/runs", { method: "POST", body: JSON.stringify(payload) });
}

export async function cancelRun(runId: string): Promise<RunSummary> {
  return api<RunSummary>(`/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
}

/** True when the backend predates /api/runs, so the caller can fall back to /api/chat. */
export function runsUnavailable(error: unknown): boolean {
  return error instanceof ApiError && [404, 405, 501].includes(error.status);
}

/** Split a streamed NDJSON buffer into complete lines and the unfinished remainder. */
export function splitNdjson(buffer: string): { lines: string[]; rest: string } {
  const parts = buffer.split("\n");
  const rest = parts.pop() ?? "";
  return { lines: parts.filter((line) => line.trim() !== ""), rest };
}

export function parseRunEvent(line: string): RunEvent {
  const event = JSON.parse(line) as RunEvent;
  if (typeof event?.type !== "string" || typeof event?.seq !== "number") {
    throw new Error("The agent returned an unreadable update.");
  }
  return event;
}

export type FollowRunOptions = {
  onEvent: (event: RunEvent) => void;
  signal?: AbortSignal;
  after?: number;
};

/** Read a run's NDJSON event stream until the server closes it (after the terminal event). */
export async function followRun(runId: string, options: FollowRunOptions): Promise<void> {
  const response = await fetch(
    apiUrl(`/runs/${encodeURIComponent(runId)}/events?after=${options.after ?? 0}`),
    { credentials: "include", signal: options.signal },
  );
  if (!response.ok || !response.body) {
    throw new ApiError("The run stream could not be opened.", response.status);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const { lines, rest } = splitNdjson(done ? `${buffer}\n` : buffer);
      buffer = rest;
      for (const line of lines) options.onEvent(parseRunEvent(line));
      if (done) return;
    }
  } finally {
    reader.releaseLock();
  }
}
