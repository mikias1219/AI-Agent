"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "@/lib/api/client";
import { getStatus } from "@/lib/api/status";
import { telegramActivity } from "@/lib/api/telegram";
import type { ActivityEvent, TelegramStatusPayload } from "@/lib/api/types";

const ACTIVITY_LIMIT = 50;

export function useTelegram() {
  const alive = useRef(true);
  const [status, setStatus] = useState<TelegramStatusPayload | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (options?: { initial?: boolean }) => {
    if (options?.initial) setLoading(true);
    setError(null);
    try {
      const [nextStatus, nextActivity] = await Promise.all([
        getStatus(),
        telegramActivity(ACTIVITY_LIMIT),
      ]);
      if (!alive.current) return;
      setStatus(nextStatus.telegram);
      setActivity(nextActivity);
    } catch (err) {
      if (alive.current) setError(apiErrorMessage(err));
    } finally {
      if (options?.initial && alive.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    void refresh({ initial: true });
    return () => {
      alive.current = false;
    };
  }, [refresh]);

  return {
    status,
    activity,
    loading,
    error,
    refresh,
  };
}
