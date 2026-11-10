import { api } from "./client";
import type { AuthStatus, LoginResponse, RegisterResponse, User } from "./types";

export type { AuthStatus, User };

export async function getAuth(): Promise<AuthStatus> {
  return api<AuthStatus>("/auth");
}

export async function login(
  email: string | null,
  password: string,
): Promise<{ authenticated: true; user: User }> {
  const payload: { password: string; email?: string } = { password };
  if (email !== null) {
    payload.email = email;
  }
  return api<LoginResponse>("/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function register(
  name: string,
  email: string,
  password: string,
): Promise<{ registered: true }> {
  return api<RegisterResponse>("/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function logout(): Promise<void> {
  await api<{ authenticated: false }>("/logout", { method: "POST", body: JSON.stringify({}) });
}
