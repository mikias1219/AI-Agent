import { apiUrl, ApiError } from "./client";

async function demoApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(`/demo${path}`), {
    credentials: "include",
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    throw new ApiError("The demo API returned an unreadable response.", response.status);
  }
  if (!response.ok) {
    const detail = (data as { detail?: string })?.detail;
    throw new ApiError(
      typeof detail === "string" ? detail : `Demo request failed (${response.status}).`,
      response.status,
    );
  }
  return data as T;
}

export type DemoSession = {
  demo: true;
  owner: string;
  banner: string;
  tasks: { id: string; title: string; status: string }[];
  memories: { id: string; kind: string; content: string }[];
};

export async function openDemoSession(): Promise<DemoSession> {
  return demoApi<DemoSession>("/session", { method: "POST", body: "{}" });
}

export async function demoChat(
  text: string,
  sessionId?: string,
): Promise<{
  session_id: string;
  reply: string;
}> {
  return demoApi("/chat", {
    method: "POST",
    body: JSON.stringify({ text, session_id: sessionId }),
  });
}

export async function demoCreateTask(title: string): Promise<{ id: string; title: string }> {
  return demoApi("/tasks", { method: "POST", body: JSON.stringify({ title }) });
}
