import { getAuth } from "@/lib/api/auth";
import type { AuthStatus, User } from "@/lib/api/types";

/** Backend dashboard cookie; HttpOnly — not readable from JS, documented for operators. */
export const SESSION_COOKIE_NAME = "personal_agent_session";

export const SESSION_EXPIRED_EVENT = "session-expired";

export function dispatchSessionExpired(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
}

export function isAuthenticated(status: AuthStatus | null | undefined): boolean {
  return Boolean(status?.authenticated);
}

export function sessionUser(status: AuthStatus | null | undefined): User | null {
  return status?.authenticated ? status.user : null;
}

export function displayName(user: User | null | undefined): string {
  const name = user?.name?.trim();
  return name || "Friend";
}

export async function readSession(): Promise<AuthStatus> {
  return getAuth();
}
