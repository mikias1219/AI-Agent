const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${API_BASE}/api${path}`;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    credentials: "include",
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    body: options.body === undefined ? undefined : (options.body as BodyInit),
  });
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    throw new ApiError("The backend returned an unreadable response.", response.status);
  }
  if (!response.ok) {
    const detail = (data as { detail?: string | { msg: string }[] })?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg).join(". ")
      : typeof detail === "string"
        ? detail
        : `Request failed (${response.status}).`;
    throw new ApiError(message, response.status);
  }
  return data as T;
}
