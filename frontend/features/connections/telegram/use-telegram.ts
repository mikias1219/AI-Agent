"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "@/lib/api/client";
import { getStatus } from "@/lib/api/status";
import {
  startTelegram,
  stopTelegram,
  telegramActivity,
  verifyTelegram,
  type TelegramIdentity,
} from "@/lib/api/telegram";
import type { ActivityEvent, TelegramStatusPayload } from "@/lib/api/types";

const ACTIVITY_LIMIT = 50;
const WATCH_ATTEMPTS = 6;
const WATCH_INTERVAL_MS = 2000;

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isListening(status: TelegramStatusPayload) {
  return (
    status.managed ||
    status.runtime === "starting" ||
    status.runtime === "polling" ||
    status.runtime === "responding" ||
    status.runtime === "running"
  );
}

export function useTelegram() {
  const alive = useRef(true);
  const watchId = useRef(0);
  const [status, setStatus] = useState<TelegramStatusPayload | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [identity, setIdentity] = useState<TelegramIdentity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<null | "verify" | "start" | "stop">(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);

  const refresh = useCallback(async (options?: { initial?: boolean }) => {
    if (options?.initial) setLoading(true);
    setError(null);
    try {
      const [nextStatus, nextActivity] = await Promise.all([
        getStatus(),
        telegramActivity(ACTIVITY_LIMIT),
      ]);
      if (!alive.current) return null;
      setStatus(nextStatus.telegram);
      setActivity(nextActivity);
      if (!nextStatus.telegram.managed) setStopping(false);
      return nextStatus.telegram;
    } catch (err) {
      if (alive.current) setError(apiErrorMessage(err));
      return null;
    } finally {
      if (options?.initial && alive.current) setLoading(false);
    }
  }, []);

  const watchUntil = useCallback(
    async (goal: "running" | "stopped") => {
      const id = watchId.current + 1;
      watchId.current = id;
      for (let attempt = 0; attempt < WATCH_ATTEMPTS; attempt += 1) {
        if (attempt > 0) await wait(WATCH_INTERVAL_MS);
        if (!alive.current || watchId.current !== id) return;
        const next = await refresh();
        if (!next || !alive.current || watchId.current !== id) return;
        if (goal === "running" && isListening(next)) return;
        if (goal === "stopped" && !next.managed) return;
      }
      if (alive.current && watchId.current === id && goal === "stopped") setStopping(false);
    },
    [refresh],
  );

  useEffect(() => {
    alive.current = true;
    void refresh({ initial: true });
    return () => {
      alive.current = false;
      watchId.current += 1;
    };
  }, [refresh]);

  async function verify() {
    setBusy("verify");
    setActionError(null);
    setNotice(null);
    try {
      const next = await verifyTelegram();
      if (!alive.current) return;
      setIdentity(next);
      const handle = next.username ? ` as @${next.username}` : "";
      setNotice(`Telegram verified${handle}. No message was sent.`);
      await refresh();
    } catch (err) {
      if (alive.current) setActionError(apiErrorMessage(err));
    } finally {
      if (alive.current) setBusy(null);
    }
  }

  async function start() {
    setBusy("start");
    setActionError(null);
    setNotice(null);
    setStopping(false);
    try {
      await startTelegram();
      if (!alive.current) return;
      setNotice("Start requested. Status updates as the heartbeat arrives.");
      void watchUntil("running");
    } catch (err) {
      if (alive.current) setActionError(apiErrorMessage(err));
    } finally {
      if (alive.current) setBusy(null);
    }
  }

  async function stop() {
    setBusy("stop");
    setActionError(null);
    setNotice(null);
    setStopping(true);
    try {
      await stopTelegram();
      if (!alive.current) return;
      setNotice("Stop requested. Status updates when the current poll finishes.");
      void watchUntil("stopped");
    } catch (err) {
      if (!alive.current) return;
      setStopping(false);
      setActionError(apiErrorMessage(err));
    } finally {
      if (alive.current) setBusy(null);
    }
  }

  return {
    status,
    activity,
    identity,
    loading,
    error,
    busy,
    actionError,
    notice,
    stopping,
    refresh,
    verify,
    start,
    stop,
  };
}
