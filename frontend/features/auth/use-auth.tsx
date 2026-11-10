"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getAuth, login as apiLogin, logout as apiLogout, register as apiRegister } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import type { AuthStatus } from "@/lib/api/types";

export type UseAuthValue = {
  status: AuthStatus | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  login: (email: string | null, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<UseAuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await getAuth();
      setStatus(next);
      setError(null);
    } catch (err) {
      setStatus(null);
      setError(err instanceof Error ? err.message : "Could not load auth status.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string | null, password: string) => {
      await apiLogin(email, password);
      await refresh();
    },
    [refresh],
  );

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      await apiRegister(name, email, password);
    },
    [],
  );

  const logout = useCallback(async () => {
    await apiLogout();
    await refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ status, loading, error, refresh, login, register, logout }),
    [status, loading, error, refresh, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): UseAuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

export function authErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Something went wrong. Try again.";
}
